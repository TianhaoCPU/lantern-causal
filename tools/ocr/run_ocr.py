#!/usr/bin/env python3
"""Resumable, one-process-per-GPU Unlimited-OCR-2 literature extraction."""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import datetime as dt
import fcntl
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback

_paths_file = Path(__file__).resolve().parents[2] / "configs/local.paths.json"
_paths = json.loads(_paths_file.read_text()) if _paths_file.exists() else {}
_asset_root = os.environ.get("LANTERN_ASSET_ROOT") or _paths.get("source_workspace")
if not _asset_root:
    raise SystemExit("Set LANTERN_ASSET_ROOT or configs/local.paths.json before using the optional OCR tools.")
ROOT = Path(_asset_root).expanduser().resolve()
OUT = ROOT / "literature_ocr"
MODEL = Path(os.environ.get("LANTERN_OCR_MODEL") or _paths.get("ocr_model") or ROOT / "Unlimited-OCR-2")
PYTHON = Path(os.environ.get("LANTERN_OCR_PYTHON", sys.executable))
SCRIPT = Path(__file__).resolve()
CONFIG = {
    "model_id": "PaddlePaddle/Unlimited-OCR-2",
    "pipeline_version": 2,
    "dpi": 200,
    "base_size": 1024,
    "image_size": 640,
    "crop_mode": True,
    "max_crops": 6,
    "max_new_tokens": 8192,
    "retry_max_new_tokens": 16384,
    "max_page_tokens": 20000,
    "no_repeat_ngram_size": 35,
    "ngram_window": 128,
    "temperature": 0.0,
    "dtype": "bfloat16",
    "attention_implementation": "eager",
    "processing_unit": "single_pdf_page",
    "auto_orientation": "dominant_native_text_direction",
    "orientation_min_fraction": 0.6,
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_json(path, obj):
    atomic_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(event, **fields):
    print(json.dumps({"time": now(), "event": event, **fields}, ensure_ascii=False), flush=True)


def prepare():
    import fitz

    for folder in ("json", "txt", "markdown", "pages", "logs", "workers", "runs"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    metadata = {}
    with (ROOT / "literature_downloads/manifest.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("file"):
                metadata[Path(row["file"]).stem] = row
    model_hashes = {p.name: digest(p) for p in sorted(MODEL.glob("*.py"))}
    for name in ("config.json", "model.safetensors.index.json", "tokenizer_config.json"):
        model_hashes[name] = digest(MODEL / name)
    signature = hashlib.sha256(json.dumps({"config": CONFIG, "model": model_hashes}, sort_keys=True).encode()).hexdigest()
    docs = []
    for p in sorted((ROOT / "literature_downloads").rglob("*.pdf")):
        with fitz.open(p) as pdf:
            if pdf.needs_pass:
                raise ValueError(f"Encrypted PDF: {p}")
            pages = len(pdf)
            pdf_metadata = pdf.metadata
        docs.append({"document_id": p.stem, "source_pdf": str(p.relative_to(ROOT)),
                     "sha256": digest(p), "page_count": pages,
                     "bibliography": metadata.get(p.stem, {}), "pdf_metadata": pdf_metadata})
    assert len({d["document_id"] for d in docs}) == len(docs), "Duplicate PDF names"
    inventory = {"created_at": now(), "config": CONFIG, "signature": signature,
                 "model_code_hashes": model_hashes, "document_count": len(docs),
                 "total_pages": sum(d["page_count"] for d in docs), "documents": docs}
    atomic_json(OUT / "inventory.json", inventory)
    emit("inventory_ready", documents=len(docs), pages=inventory["total_pages"], signature=signature)
    return inventory


def page_path(document_id, page_number):
    return OUT / "pages" / document_id / f"page_{page_number:04d}.json"


def valid_page(value, document, signature, page_number):
    return (isinstance(value, dict) and value.get("source_sha256") == document["sha256"]
            and value.get("pipeline_signature") == signature
            and value.get("page_number") == page_number and value.get("status") == "ok")


def parse_blocks(raw):
    """Parse the checkpoint's actual <BLOCK>type[box]<FORK>content format."""
    blocks = []
    pattern = r"<BLOCK>(.*?)<FORK>(.*?)(?=<BLOCK>|\Z)"
    for i, match in enumerate(re.finditer(pattern, raw, re.S), 1):
        header, content = match.groups()
        label = re.match(r"\s*([\w-]+)", header)
        level = re.search(r"<LEVEL(\d+)>", header)
        box = re.search(r"\[[^\[\]]+\]", header)
        bbox = None
        if box:
            try:
                candidate = ast.literal_eval(box.group())
                if len(candidate) == 4 and all(isinstance(n, (int, float)) for n in candidate):
                    bbox = list(candidate)
            except (ValueError, SyntaxError, TypeError):
                pass
        blocks.append({"order": i, "type": label.group(1) if label else "unknown",
                       "heading_level": int(level.group(1)) if level else None,
                       "bbox_model": bbox, "raw_header": header.strip(),
                       "content": clean_markers(content).strip()})
    if not blocks:
        blocks = [{"order": 1, "type": "unparsed", "heading_level": None,
                   "bbox_model": None, "raw_header": None,
                   "content": clean_markers(raw).strip()}]
    return blocks


def clean_markers(text):
    text = re.sub(r"<(?:PAGE|BLOCK|FORK|LEVEL\d+)>", "", text)
    return text.replace("<｜end▁of▁sentence｜>", "").replace("<|endoftext|>", "")


def plain_content(text):
    # Keep equations and table values, without emitting table HTML into TXT.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", "\t", text, flags=re.I)
    text = re.sub(r"</tr>", "\n", text, flags=re.I)
    text = re.sub(r"</?(?:table|thead|tbody|tfoot|tr|td|th|caption|sup|sub|p|div|span)\b[^>]*>", "", text, flags=re.I)
    return html.unescape(text).strip()


def page_strings(blocks):
    markdown, plain = [], []
    for block in blocks:
        content = block["content"].strip()
        if not content:
            continue
        level = block.get("heading_level")
        markdown.append(("#" * min(level, 6) + " " if level else "") + content)
        plain.append(plain_content(content))
    return "\n\n".join(markdown), "\n\n".join(plain)


def lexical_metrics(native, extracted):
    words = lambda s: re.findall(r"[a-z0-9]+", s.lower())
    reference = collections.Counter(words(native))
    candidate = collections.Counter(words(extracted))
    shared = sum((reference & candidate).values())
    return {"native_pdf_word_count": sum(reference.values()),
            "ocr_word_count": sum(candidate.values()),
            "native_word_recall": round(shared / sum(reference.values()), 4) if reference else None,
            "ocr_word_precision_vs_native": round(shared / sum(candidate.values()), 4) if candidate else None,
            "note": "PDF text is a diagnostic reference, not OCR ground truth; it is never substituted for OCR."}


def orientation(page):
    """Use PDF line directions to make sideways body/table text horizontal."""
    counts = collections.Counter()
    for block in page.get_text("dict", flags=0)["blocks"]:
        for line in block.get("lines", []):
            dx, dy = line.get("dir", (1.0, 0.0))
            angle = int(round(math.degrees(math.atan2(dy, dx)) / 90) * 90) % 360
            # get_pixmap honors the PDF page rotation; text coordinates do not.
            effective_angle = (angle + page.rotation) % 360
            counts[effective_angle] += sum(len(span.get("text", "")) for span in line.get("spans", []))
    total = sum(counts.values())
    dominant, count = counts.most_common(1)[0] if counts else (0, 0)
    fraction = count / total if total else 0.0
    rotation = dominant if total >= 50 and fraction >= CONFIG["orientation_min_fraction"] else 0
    return {"rotation_degrees_ccw": rotation, "pdf_page_rotation": page.rotation,
            "direction_character_counts": dict(counts), "dominant_fraction": round(fraction, 4),
            "method": CONFIG["auto_orientation"]}


def assemble(document, inventory):
    pages = [read_json(page_path(document["document_id"], n)) for n in range(1, document["page_count"] + 1)]
    complete = all(valid_page(p, document, inventory["signature"], n) for n, p in enumerate(pages, 1))
    pages = [p for p in pages if p]
    warnings = [f"page {p['page_number']}: {w}" for p in pages for w in p.get("warnings", [])]
    record = {"schema_version": "1.0", "document_id": document["document_id"],
              "status": "complete" if complete else "incomplete", "updated_at": now(),
              "source": document, "engine": {"config": inventory["config"],
              "pipeline_signature": inventory["signature"]}, "page_count": document["page_count"],
              "processed_pages": len(pages), "warnings": warnings, "pages": pages}
    record["text"] = "\n\n".join(f"[Page {p['page_number']}]\n{p['text']}" for p in pages)
    record["markdown"] = "\n\n".join(f"<!-- Page {p['page_number']} -->\n{p['markdown']}" for p in pages)
    name = document["document_id"]
    bibliography = document["bibliography"]
    preamble = (f"Title: {bibliography.get('title', '')}\nPMID: {bibliography.get('pmid', '')}\n"
                f"DOI: {bibliography.get('doi', '')}\nSource: {document['source_pdf']}\n"
                f"OCR model: {CONFIG['model_id']}\nStatus: {record['status']}\n\n")
    atomic_text(OUT / "txt" / f"{name}.txt", preamble + record["text"] + "\n")
    atomic_text(OUT / "markdown" / f"{name}.md", record["markdown"] + "\n")
    # JSON is the commit marker: write after the companion text files.
    atomic_json(OUT / "json" / f"{name}.json", record)
    emit("document_saved", document=name, status=record["status"], pages=len(pages), warnings=len(warnings))
    return complete


def worker(gpu, only=None):
    # Physical nvidia-smi UUIDs prevent CUDA enumeration from selecting a different card.
    gpu_uuid = subprocess.check_output(["nvidia-smi", "-i", str(gpu), "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    os.environ.update(CUDA_VISIBLE_DEVICES=gpu_uuid, CUDA_DEVICE_ORDER="PCI_BUS_ID",
                      TOKENIZERS_PARALLELISM="false", HF_HUB_OFFLINE="1",
                      PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")
    import fitz
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(4)
    torch.manual_seed(0)
    inventory = read_json(OUT / "inventory.json")
    if not inventory:
        raise RuntimeError("Run prepare first")
    documents = inventory["documents"]
    if only:
        documents = [d for d in documents if d["document_id"] == only]
        if not documents:
            raise ValueError(f"Unknown document: {only}")
    state_path = OUT / "workers" / f"gpu_{gpu}.json"
    signature = inventory["signature"]
    pending = [d for d in documents if any(not valid_page(read_json(page_path(d["document_id"], n)), d, signature, n)
               for n in range(1, d["page_count"] + 1))]
    emit("worker_start", gpu=gpu, gpu_uuid=gpu_uuid, pending_documents=len(pending), pid=os.getpid())
    model = tokenizer = None
    errors = 0
    fatal = None
    try:
        if pending:
            atomic_json(state_path, {"status": "loading_model", "gpu": gpu, "pid": os.getpid(), "time": now()})
            tokenizer = AutoTokenizer.from_pretrained(str(MODEL), trust_remote_code=True, local_files_only=True)
            model = AutoModel.from_pretrained(str(MODEL), trust_remote_code=True, local_files_only=True,
                use_safetensors=True, torch_dtype=torch.bfloat16, attn_implementation="eager").eval().cuda()
            assert torch.cuda.device_count() == 1
            emit("model_ready", gpu=gpu, name=torch.cuda.get_device_name(), torch=torch.__version__)
        for document in documents:
            name = document["document_id"]
            lock_path = OUT / "pages" / name / ".lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue  # The other GPU has claimed this document.
                finished = all(valid_page(read_json(page_path(name, n)), document, signature, n)
                               for n in range(1, document["page_count"] + 1))
                if finished:
                    existing = read_json(OUT / "json" / f"{name}.json", {})
                    if existing.get("status") != "complete" or existing.get("engine", {}).get("pipeline_signature") != signature:
                        assemble(document, inventory)
                    continue
                if model is None:
                    raise RuntimeError("Model unavailable for pending document")
                with fitz.open(ROOT / document["source_pdf"]) as pdf:
                    for number, page in enumerate(pdf, 1):
                        dest = page_path(name, number)
                        if valid_page(read_json(dest), document, signature, number):
                            continue
                        atomic_json(state_path, {"status": "running", "gpu": gpu, "gpu_uuid": gpu_uuid,
                            "pid": os.getpid(), "document_id": name, "page": number,
                            "document_pages": len(pdf), "page_started_at": now()})
                        emit("page_start", gpu=gpu, document=name, page=number, total=len(pdf))
                        try:
                            torch.cuda.reset_peak_memory_stats()
                            pix = page.get_pixmap(dpi=CONFIG["dpi"], colorspace=fitz.csRGB, alpha=False)
                            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            direction = orientation(page)
                            if direction["rotation_degrees_ccw"]:
                                image = image.rotate(direction["rotation_degrees_ccw"], expand=True)
                                emit("page_oriented", gpu=gpu, document=name, page=number, **direction)
                            native = page.get_text()
                            attempts = []
                            result = None
                            for cap in (CONFIG["max_new_tokens"], CONFIG["retry_max_new_tokens"]):
                                with torch.inference_mode():
                                    result = model.infer(tokenizer, image_file=image,
                                        crop_mode=True, base_size=CONFIG["base_size"], image_size=CONFIG["image_size"],
                                        max_crops=CONFIG["max_crops"], max_new_tokens=cap,
                                        max_page_tokens=CONFIG["max_page_tokens"], no_repeat_ngram_size=35,
                                        ngram_window=128, eval_mode=True, return_dict=True,
                                        temperature=0.0, save_results=False, tps_interval=1024)
                                attempts.append({"max_new_tokens": cap, "tokens": len(result["token_ids"]),
                                                 "finish_reason": result["finish_reason"], "seconds": result["time"]})
                                if result["finish_reason"] == "stop":
                                    break
                            blocks = parse_blocks(result["text"])
                            markdown, text = page_strings(blocks)
                            metrics = lexical_metrics(native, text)
                            warnings = []
                            status = "ok"
                            if result["finish_reason"] != "stop":
                                warnings.append("generation_reached_token_limit")
                                status = "needs_review"
                            if result["num_pages_out"] != 1:
                                warnings.append("unexpected_output_page_count")
                                status = "needs_review"
                            if not text.strip() and native.strip():
                                warnings.append("empty_ocr_for_nonempty_pdf_page")
                                status = "needs_review"
                            if metrics["native_pdf_word_count"] >= 100 and metrics["native_word_recall"] < 0.65:
                                warnings.append("low_word_overlap_with_native_pdf_text")
                            value = {"schema_version": "1.0", "document_id": name, "page_number": number,
                                "source_sha256": document["sha256"], "pipeline_signature": signature,
                                "status": status, "completed_at": now(), "gpu_physical_index": gpu,
                                "gpu_uuid": gpu_uuid, "render": {"dpi": CONFIG["dpi"], "width": image.width,
                                "height": image.height, "pdf_width_points": page.rect.width, "pdf_height_points": page.rect.height,
                                "orientation": direction},
                                "raw_ocr": result["text"], "text": text, "markdown": markdown, "blocks": blocks,
                                "generation": {"finish_reason": result["finish_reason"], "output_tokens": len(result["token_ids"]),
                                "output_pages": result["num_pages_out"], "attempts": attempts,
                                "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated() / 2**20, 2)},
                                "quality_diagnostics": metrics, "warnings": warnings}
                            atomic_json(dest, value)
                            del image, pix, result
                            emit("page_saved", gpu=gpu, document=name, page=number, status=status,
                                 chars=len(text), tokens=value["generation"]["output_tokens"],
                                 seconds=round(sum(a["seconds"] for a in attempts), 2), warnings=warnings)
                        except Exception as exc:
                            errors += 1
                            atomic_json(dest.with_suffix(".error.json"), {"time": now(), "document": name,
                                "page": number, "gpu": gpu, "error": repr(exc), "traceback": traceback.format_exc()})
                            emit("page_error", gpu=gpu, document=name, page=number, error=repr(exc))
                            traceback.print_exc()
                            if isinstance(exc, torch.cuda.OutOfMemoryError):
                                torch.cuda.empty_cache()
                            continue
                assemble(document, inventory)
    except BaseException as exc:
        fatal = repr(exc)
        raise
    finally:
        atomic_json(state_path, {"status": "failed" if fatal else "finished", "gpu": gpu,
            "pid": os.getpid(), "time": now(), "page_errors": errors, "fatal_error": fatal})
    return 0 if errors == 0 else 2


def status(print_output=True):
    inventory = read_json(OUT / "inventory.json", {"documents": [], "document_count": 0, "total_pages": 0})
    completed_docs, completed_pages, warnings, failures = 0, 0, 0, 0
    for d in inventory["documents"]:
        pages = [read_json(page_path(d["document_id"], n)) for n in range(1, d["page_count"] + 1)]
        valid = [valid_page(p, d, inventory["signature"], n) for n, p in enumerate(pages, 1)]
        completed_pages += sum(valid)
        warnings += sum(bool(p.get("warnings")) for p in pages if isinstance(p, dict))
        failures += sum((OUT / "pages" / d["document_id"] / f"page_{n:04d}.error.json").exists()
                        and not valid[n - 1] for n in range(1, d["page_count"] + 1))
        record = read_json(OUT / "json" / f"{d['document_id']}.json", {})
        completed_docs += all(valid) and record.get("status") == "complete"
    workers = [read_json(p) for p in sorted((OUT / "workers").glob("gpu_*.json"))]
    for worker_state in workers:
        if not worker_state:
            continue
        try:
            os.kill(worker_state.get("pid", -1), 0)
            worker_state["process_alive"] = True
        except (ProcessLookupError, PermissionError):
            worker_state["process_alive"] = False
    summary = {"time": now(), "documents_total": inventory["document_count"], "documents_complete": completed_docs,
               "pages_total": inventory["total_pages"], "pages_complete": completed_pages,
               "pages_with_quality_warnings": warnings, "pages_with_unresolved_errors": failures,
               "workers": workers}
    atomic_json(OUT / "progress.json", summary)
    if print_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def supervise(gpus):
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    with (OUT / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        processes = []
        handles = []
        stopping = False

        def stop_children(signum, frame):
            nonlocal stopping
            stopping = True
            for p in processes:
                if p.poll() is None:
                    p.terminate()

        signal.signal(signal.SIGTERM, stop_children)
        signal.signal(signal.SIGINT, stop_children)
        started = now()
        emit("supervisor_start", pid=os.getpid(), gpus=gpus)
        for gpu in gpus:
            log = (OUT / "logs" / f"gpu_{gpu}.log").open("a")
            handles.append(log)
            p = subprocess.Popen([str(PYTHON), "-u", str(SCRIPT), "worker", "--gpu", str(gpu)],
                                 cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            processes.append(p)
        atomic_json(OUT / "run.json", {"status": "running", "started_at": started, "supervisor_pid": os.getpid(),
                    "workers": [{"gpu": gpu, "pid": p.pid} for gpu, p in zip(gpus, processes)]})
        while any(p.poll() is None for p in processes):
            status(False)
            time.sleep(15)
        summary = status(False)
        final = "stopped" if stopping else ("complete" if summary["documents_complete"] == summary["documents_total"] else "finished_with_issues")
        atomic_json(OUT / "run.json", {"status": final, "started_at": started, "finished_at": now(),
                    "supervisor_pid": os.getpid(), "workers": [{"gpu": gpu, "pid": p.pid, "returncode": p.returncode}
                    for gpu, p in zip(gpus, processes)], "summary": summary})
        for log in handles:
            log.close()
        emit("supervisor_finished", status=final, **summary)


def start(gpus):
    prepare()
    # Refuse a duplicate launch before detaching.
    with (OUT / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with (OUT / "logs/supervisor.log").open("a") as log:
        process = subprocess.Popen([str(PYTHON), "-u", str(SCRIPT), "supervise", "--gpus", *map(str, gpus)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True)
    atomic_text(OUT / "supervisor.pid", str(process.pid) + "\n")
    emit("detached", pid=process.pid, gpus=gpus, log=str(OUT / "logs/supervisor.log"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    p = sub.add_parser("worker")
    p.add_argument("--gpu", type=int, required=True)
    p.add_argument("--only", help="Process one document ID for the full-document smoke test")
    for name in ("start", "supervise"):
        p = sub.add_parser(name)
        p.add_argument("--gpus", nargs="+", type=int, default=[2, 6])
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "worker":
        raise SystemExit(worker(args.gpu, args.only))
    elif args.command == "status":
        status()
    elif args.command == "start":
        start(args.gpus)
    else:
        supervise(args.gpus)


if __name__ == "__main__":
    main()

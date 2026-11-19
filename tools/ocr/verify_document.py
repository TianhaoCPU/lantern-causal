"""Verify a completed document and save a readable full-document smoke-test report."""

import argparse
import json
from pathlib import Path

import fitz

from run_ocr import CONFIG, OUT, ROOT, atomic_json, now, parse_blocks, plain_content, read_json


def verify(name):
    inventory = read_json(OUT / "inventory.json")
    source = next(d for d in inventory["documents"] if d["document_id"] == name)
    record = read_json(OUT / "json" / f"{name}.json")
    with fitz.open(ROOT / source["source_pdf"]) as pdf:
        assert record["status"] == "complete"
        assert record["page_count"] == record["processed_pages"] == len(pdf)
        assert [p["page_number"] for p in record["pages"]] == list(range(1, len(pdf) + 1))
    text_path = OUT / "txt" / f"{name}.txt"
    text = text_path.read_text(encoding="utf-8")
    markdown = (OUT / "markdown" / f"{name}.md").read_text(encoding="utf-8")
    assert record["text"] in text
    assert record["markdown"].strip() == markdown.strip()
    page_reports = []
    for page in record["pages"]:
        assert page["status"] == "ok"
        assert page["generation"]["finish_reason"] == "stop"
        assert page["generation"]["output_pages"] == 1
        assert page["pipeline_signature"] == inventory["signature"]
        assert page["source_sha256"] == source["sha256"]
        assert page["blocks"] == parse_blocks(page["raw_ocr"])
        assert not any(marker in page["text"] for marker in ("<PAGE>", "<BLOCK>", "<FORK>", "<LEVEL"))
        assert page["text"] in text
        page_reports.append({"page": page["page_number"], "chars": len(page["text"]),
            "blocks": len(page["blocks"]), "tokens": page["generation"]["output_tokens"],
            "generation_seconds": round(sum(a["seconds"] for a in page["generation"]["attempts"]), 2),
            "peak_gpu_memory_mib": page["generation"]["peak_gpu_memory_mib"],
            "native_word_recall": page["quality_diagnostics"]["native_word_recall"],
            "warnings": page["warnings"]})
    # A title from the source manifest must be visible in the OCR result.
    title = source["bibliography"]["title"].lower().rstrip(".")
    import re
    normalize = lambda s: " ".join(re.findall(r"[a-z0-9]+", s.lower()))
    assert normalize(title) in normalize(record["text"]), "Bibliographic title missing from OCR output"
    report = {"verified_at": now(), "status": "PASS", "document_id": name,
        "title": source["bibliography"]["title"], "source_pdf": source["source_pdf"],
        "model": CONFIG["model_id"], "gpu_indices": sorted({p["gpu_physical_index"] for p in record["pages"]}),
        "pages": page_reports, "text_characters": len(record["text"]),
        "block_count": sum(len(p["blocks"]) for p in record["pages"]),
        "all_pages_finished_without_token_truncation": True,
        "native_text_diagnostic": "Word overlap is a diagnostic, not an accuracy estimate against human transcription.",
        "json": str((OUT / "json" / f"{name}.json").relative_to(ROOT)),
        "txt": str(text_path.relative_to(ROOT))}
    atomic_json(OUT / "first_document_test_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("document_id")
    verify(parser.parse_args().document_id)

#!/usr/bin/env python3
"""Build a PMID-indexed literature corpus from local PubMed and OCR outputs.

Uses only the Python standard library. Original files are read-only. A build
stages its outputs before publishing them to avoid leaving a partial corpus.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tempfile


VERSION = "1.0"
HEADLINE = re.compile(
    r"^(\d+)\. \*\*(.*?)\*\* \((\d{4}) · (.*?) · PMID: (\d+)\)\s*$",
    re.MULTILINE,
)
# These are OCR layout instructions, not article content or numeric notation.
MERGE_LINE = re.compile(r"(?m)^[ \t]*<MERGE>[ \t]*(?:\n|$)")
GENERATED = ("txt", "abstracts", "json", "sources", "schema")
SUMMARY_FILES = (
    "papers.jsonl", "index.json", "index.csv", "quality_report.json",
    "dataset_info.json",
)
INPUTS = {
    "pubmed_index.txt": "backup/pubmed_mimic_risk_factors_results.md",
    "download_manifest.csv": "literature_downloads/manifest.csv",
    "abstract_screening.csv": "mimic_new_risk_factors_summary.csv",
    "replication_registry.csv": "MIMIC_case_复现登记表.csv",
    "ocr_inventory.json": "literature_ocr/inventory.json",
    "ocr_progress.json": "literature_ocr/progress.json",
}


def digest(data: bytes) -> str:
    """Return the SHA-256 of bytes, including the exact text-file encoding."""
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    """Hash a file in bounded-size chunks without modifying it."""
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: object) -> None:
    """Write readable, strict UTF-8 JSON with a trailing newline."""
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_table(data: bytes, key: str) -> dict[str, dict[str, str]]:
    """Read a UTF-8 CSV into a unique-ID mapping and reject duplicate rows."""
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    mapped = {row[key].strip(): row for row in rows}
    if len(mapped) != len(rows) or "" in mapped:
        raise ValueError(f"Nonunique or blank CSV identifier: {key}")
    return mapped


def parse_pubmed(data: bytes) -> dict[str, dict]:
    """Parse the archived report without guessing missing bibliographic data."""
    text = data.decode("utf-8")
    matches = list(HEADLINE.finditer(text))
    records = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end]
        abstract = re.search(r"^\s*摘要：([^\n]+)$", body, re.MULTILINE)
        doi = re.search(r"^\s*DOI: ([^\n]+)$", body, re.MULTILINE)
        lines = [line.strip() for line in body.strip().splitlines()]
        number, title, year, journal, pmid = match.groups()
        if pmid in records or not abstract:
            raise ValueError(f"Repeated PMID or unavailable abstract: {pmid}")
        records[pmid] = {
            "source_number": int(number), "title": title,
            "publication_year": int(year), "journal": journal,
            # The report lists at most three authors followed by "et al.".
            "authors_display": lines[0] if lines and not lines[0].startswith(
                ("DOI:", "https://", "摘要：")
            ) else None,
            "doi": doi.group(1).strip() if doi else None,
            "abstract": abstract.group(1).strip(),
        }
    return records


def clean_layout(text: str) -> tuple[str, int]:
    """Remove only standalone MERGE instructions and return the removal count."""
    return MERGE_LINE.subn("", text)


def normalize_ocr(ocr: dict) -> tuple[str, list[dict], list[dict], list[dict], int]:
    """Assemble full text with exact page offsets, headings, and table HTML.

    Offsets index Python Unicode characters in the output text and exclude page
    markers. Their half-open slices equal the normalized source page text.
    """
    pages, headings, tables, pieces = [], [], [], []
    cursor = removed = 0
    for position, page in enumerate(ocr["pages"]):
        page_number = page["page_number"]
        cleaned, count = clean_layout(page["text"])
        removed += count
        prefix = ("\n\n" if position else "") + f"[Page {page_number}]\n"
        cursor += len(prefix)
        start = cursor
        pieces.extend((prefix, cleaned))
        cursor += len(cleaned)
        pages.append({
            "page_number": page_number, "char_start": start, "char_end": cursor,
            "block_count": len(page["blocks"]), "status": page["status"],
            "warnings": page.get("warnings", []),
            "quality_diagnostics": page.get("quality_diagnostics", {}),
            "generation_finish_reason": page["generation"]["finish_reason"],
            "rotation_degrees_ccw": page["render"]["orientation"]["rotation_degrees_ccw"],
        })
        for block in page["blocks"]:
            shared = {"page_number": page_number, "block_order": block["order"]}
            if block["type"] == "title" and block["content"].strip():
                title, _ = clean_layout(block["content"])
                headings.append({
                    **shared, "level": block.get("heading_level"), "text": title,
                })
            if block["type"] == "table":
                tables.append({
                    **shared, "html": block["content"],
                    "bbox_model": block["bbox_model"],
                })
    # The same trailing newline is present in both the TXT and JSON text field.
    return "".join(pieces) + "\n", pages, headings, tables, removed


def paper_schema() -> dict:
    """Define the public record contract, including explicit absent full text."""
    nullable_string = {"type": ["string", "null"]}
    properties = {
        "schema_version": {"const": VERSION}, "pmid": {"type": "string", "pattern": "^[0-9]+$"},
        "source_document_id": {"type": "string"},
        "source_number": {"type": "integer", "minimum": 1}, "title": {"type": "string"},
        "publication_year": {"type": "integer"}, "journal": {"type": "string"},
        "authors_display": nullable_string, "doi": nullable_string,
        "pmcid": nullable_string, "pubmed_url": {"type": "string"},
        "abstract": {"type": "string", "minLength": 1},
        "full_text_available": {"type": "boolean"},
        "content_type": {"enum": ["ocr_full_text", "abstract_only"]},
        "text": nullable_string, "text_sha256": nullable_string,
        "page_count": {"type": ["integer", "null"], "minimum": 1},
        "pages": {"type": "array", "items": {
            "type": "object",
            "required": ["page_number", "char_start", "char_end", "warnings"],
            "properties": {
                "page_number": {"type": "integer", "minimum": 1},
                "char_start": {"type": "integer", "minimum": 0},
                "char_end": {"type": "integer", "minimum": 0},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }},
        "headings": {"type": "array"}, "tables": {"type": "array"},
        "files": {"type": "object", "required": ["txt", "json", "abstract_txt"]},
        "quality": {"type": "object"}, "provenance": {"type": "object"},
        "screening": {"type": ["object", "null"]},
        "replication_registry": {"type": "object"},
        "annotation_status": {"const": "not_causal_ground_truth"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MIMIC literature record", "type": "object",
        "additionalProperties": False, "required": list(properties),
        "properties": properties,
        "allOf": [{
            "if": {"properties": {"full_text_available": {"const": True}}},
            "then": {"properties": {
                "content_type": {"const": "ocr_full_text"},
                "text": {"type": "string", "minLength": 1},
                "text_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "page_count": {"type": "integer", "minimum": 1},
            }},
            "else": {"properties": {
                "content_type": {"const": "abstract_only"}, "text": {"type": "null"},
                "text_sha256": {"type": "null"}, "page_count": {"type": "null"},
                "pages": {"maxItems": 0}, "headings": {"maxItems": 0},
                "tables": {"maxItems": 0},
            }},
        }],
    }


def build(root: Path, stage: Path) -> dict:
    """Create validated corpus artifacts in a private staging directory."""
    for name in GENERATED:
        (stage / name).mkdir()
    snapshots = {}
    snapshot_info = []
    for filename, relative in INPUTS.items():
        data = (root / relative).read_bytes()
        snapshots[filename] = data
        (stage / "sources" / filename).write_bytes(data)
        snapshot_info.append({
            "workspace_path": relative, "snapshot": f"sources/{filename}",
            "sha256": digest(data),
        })
    manifest = read_table(snapshots["download_manifest.csv"], "pmid")
    screened = read_table(snapshots["abstract_screening.csv"], "PMID")
    registry = read_table(snapshots["replication_registry.csv"], "PMID")
    pubmed = parse_pubmed(snapshots["pubmed_index.txt"])
    inventory = json.loads(snapshots["ocr_inventory.json"])
    inv = {d["bibliography"]["pmid"]: d for d in inventory["documents"]}
    if set(manifest) != set(pubmed) or set(manifest) != set(registry):
        raise ValueError("PubMed, download and registry IDs do not agree")
    if not set(screened) <= set(manifest) or not set(inv) <= set(manifest):
        raise ValueError("Screening or OCR contains unregistered IDs")
    actual_ocr_ids = {p.stem for p in (root / "literature_ocr/json").glob("*.json")}
    if actual_ocr_ids != {d["document_id"] for d in inv.values()}:
        raise ValueError("OCR JSON files do not match the OCR inventory")
    records, index, warnings = [], [], []
    hashes = defaultdict(list)
    total_removed = total_pages = total_tables = 0
    warning_codes = Counter()
    for pmid in sorted(manifest, key=lambda key: int(manifest[key]["number"])):
        source = manifest[pmid]
        meta = pubmed[pmid]
        document_id = f"{int(source['number']):03d}_{pmid}"
        if source["title"] != meta["title"] or (source["doi"] or None) != meta["doi"]:
            raise ValueError(f"Bibliographic mismatch for PMID {pmid}")
        available = pmid in inv
        if bool(source["file"]) != available:
            raise ValueError(f"Full-text manifest and OCR disagree for {pmid}")
        (stage / "abstracts" / f"{pmid}.txt").write_text(
            meta["abstract"] + "\n", encoding="utf-8"
        )
        text = None
        pages, headings, tables, page_warnings = [], [], [], []
        removed = 0
        provenance = {
            "source_paths_relative_to": "workspace_root",
            "original_pdf": source["file"] or None,
            "original_pdf_sha256": None, "original_ocr_json": None,
            "original_ocr_json_sha256": None, "original_ocr_txt": None,
            "original_ocr_txt_sha256": None, "ocr_model": None,
            "pipeline_signature": None, "download_status": source["status"],
            "download_url": source["source_url"] or None,
            "license_code_from_manifest": source["license_code"] or None,
        }
        if available:
            original_json = root / "literature_ocr/json" / f"{document_id}.json"
            raw = original_json.read_bytes()
            ocr = json.loads(raw)
            if ocr["document_id"] != document_id or ocr["status"] != "complete":
                raise ValueError(f"Incomplete or misidentified OCR: {document_id}")
            source_meta = ocr["source"]["bibliography"]
            if source_meta["pmid"] != pmid or ocr["source"] != inv[pmid]:
                raise ValueError(f"OCR source mismatch for PMID {pmid}")
            expected_pages = list(range(1, ocr["page_count"] + 1))
            if [p["page_number"] for p in ocr["pages"]] != expected_pages:
                raise ValueError(f"Missing or unordered OCR pages: {pmid}")
            if ocr["processed_pages"] != ocr["page_count"]:
                raise ValueError(f"OCR page count mismatch: {pmid}")
            assembled = "\n\n".join(
                f"[Page {p['page_number']}]\n{p['text']}" for p in ocr["pages"]
            )
            if assembled != ocr["text"]:
                raise ValueError(f"OCR aggregate text mismatch: {pmid}")
            original_txt = root / "literature_ocr/txt" / f"{document_id}.txt"
            original_txt_bytes = original_txt.read_bytes()
            if not original_txt_bytes.decode("utf-8").endswith(ocr["text"] + "\n"):
                raise ValueError(f"OCR TXT and JSON text disagree: {pmid}")
            pdf_sha = file_digest(root / source["file"])
            if pdf_sha != ocr["source"]["sha256"]:
                raise ValueError(f"Original PDF changed: {pmid}")
            for p in ocr["pages"]:
                if p["source_sha256"] != pdf_sha or p["status"] != "ok" or not p["text"].strip():
                    raise ValueError(f"Invalid source page: {pmid}/{p['page_number']}")
            text, pages, headings, tables, removed = normalize_ocr(ocr)
            for info in pages:
                if info["warnings"]:
                    warning_codes.update(info["warnings"])
                    item = {"pmid": pmid, **info}
                    warnings.append(item)
                    page_warnings.append(info["page_number"])
            total_pages += len(pages)
            total_tables += len(tables)
            total_removed += removed
            (stage / "txt" / f"{pmid}.txt").write_text(text, encoding="utf-8")
            provenance.update({
                "original_pdf_sha256": pdf_sha,
                "original_ocr_json": original_json.relative_to(root).as_posix(),
                "original_ocr_json_sha256": digest(raw),
                "original_ocr_txt": original_txt.relative_to(root).as_posix(),
                "original_ocr_txt_sha256": digest(original_txt_bytes),
                "ocr_model": ocr["engine"]["config"]["model_id"],
                "pipeline_signature": ocr["engine"]["pipeline_signature"],
            })
            hashes[digest(text.encode("utf-8"))].append(pmid)
        quality = {
            "ocr_status": "complete" if available else "not_available",
            "pages_with_warnings": page_warnings,
            "manual_review_recommended": bool(page_warnings),
            "ocr_warnings": [
                {"page_number": p["page_number"], "codes": p["warnings"]}
                for p in pages if p["warnings"]
            ],
            "removed_standalone_merge_markers": removed,
            "figure_block_count": sum(
                b["type"] in ("image", "chart")
                for p in (ocr["pages"] if available else []) for b in p["blocks"]
            ),
            "visual_content_fully_transcribed": False if available else None,
        }
        record = {
            "schema_version": VERSION, "pmid": pmid,
            "source_document_id": document_id, **meta,
            "pmcid": source["pmcid"] or None,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "full_text_available": available,
            "content_type": "ocr_full_text" if available else "abstract_only",
            "text": text, "text_sha256": digest(text.encode("utf-8")) if available else None,
            "page_count": len(pages) if available else None,
            "pages": pages, "headings": headings, "tables": tables,
            "files": {
                "json": f"json/{pmid}.json",
                "txt": f"txt/{pmid}.txt" if available else None,
                "abstract_txt": f"abstracts/{pmid}.txt",
            },
            "quality": quality, "provenance": provenance,
            "screening": screened.get(pmid), "replication_registry": registry[pmid],
            "annotation_status": "not_causal_ground_truth",
        }
        write_json(stage / record["files"]["json"], record)
        records.append(record)
        index.append({
            "pmid": pmid, "title": meta["title"], "publication_year": meta["publication_year"],
            "doi": meta["doi"], "content_type": record["content_type"],
            "full_text_available": available, "page_count": record["page_count"],
            "text_characters": len(text) if available else 0,
            "warning_page_count": len(page_warnings),
            "abstract_screened": pmid in screened,
            **record["files"],
        })
    with (stage / "papers.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    write_json(stage / "index.json", index)
    with (stage / "index.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(index[0]))
        writer.writeheader()
        writer.writerows(index)
    duplicates = [ids for ids in hashes.values() if len(ids) > 1]
    report = {
        "records": len(records), "full_text_records": len(inv),
        "abstract_only_records": len(records) - len(inv),
        "abstract_records": len(records), "ocr_pages": total_pages,
        "ocr_table_blocks": total_tables, "abstract_screened_records": len(screened),
        "screened_with_full_text": len(set(screened) & set(inv)),
        "warning_documents": len({v["pmid"] for v in warnings}),
        "warning_pages": len(warnings), "warning_code_counts": dict(warning_codes),
        "unresolved_ocr_errors": 0, "empty_text_pages": 0,
        "removed_standalone_merge_markers": total_removed,
        "duplicate_full_text_hash_groups": duplicates,
        "missing_full_text": [
            {"pmid": r["pmid"], "title": r["title"],
             "download_status": r["provenance"]["download_status"]}
            for r in records if not r["full_text_available"]
        ],
        "pages_recommended_for_review": warnings,
        "note": "OCR word overlap is diagnostic, not manually measured accuracy.",
    }
    write_json(stage / "quality_report.json", report)
    write_json(stage / "schema/paper.schema.json", paper_schema())
    info = {
        "dataset_name": "MIMIC literature reference corpus", "version": VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "encoding": "UTF-8; index.csv is UTF-8 with BOM",
        "primary_key": "pmid", "record_schema": "schema/paper.schema.json",
        "records": len(records), "full_text_records": len(inv),
        "abstract_only_records": len(records) - len(inv),
        "training_or_test_split": None, "causal_ground_truth_provided": False,
        "normalization": [
            "Use OCR JSON page text; exclude original TXT metadata preamble.",
            "Remove only standalone <MERGE> layout instructions.",
            "Retain page markers, equations and flattened TSV tables.",
            "Retain original table HTML and OCR diagnostics in each JSON record.",
            "Keep abstract-only records explicit; text and txt path remain null.",
        ],
        "source_snapshots": snapshot_info,
        "build_script_module": "lantern_causal.datasets.build",
        "build_script_sha256": file_digest(Path(__file__)),
    }
    write_json(stage / "dataset_info.json", info)
    # A source changing during the build should not silently produce mixed data.
    for filename, relative in INPUTS.items():
        if (root / relative).read_bytes() != snapshots[filename]:
            raise ValueError(f"Source changed during build: {relative}")
    return report


def main() -> None:
    """Build into a new dataset directory or explicitly replace generated files."""
    default_output = Path.cwd() / "datasets/literature"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True,
                        help="Original workspace holding PDFs, OCR, report and metadata.")
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    root, output = args.workspace.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    targets = [output / name for name in (*GENERATED, *SUMMARY_FILES)]
    if any(p.exists() for p in targets) and not args.replace_generated:
        parser.error("Generated artifacts already exist; use --replace-generated to rebuild.")
    with tempfile.TemporaryDirectory(prefix=".build-", dir=output) as temp:
        stage = Path(temp)
        report = build(root, stage)
        for path in targets:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            (stage / path.name).rename(path)
    print(json.dumps({k: report[k] for k in (
        "records", "full_text_records", "abstract_only_records", "ocr_pages",
        "warning_documents", "warning_pages",
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()

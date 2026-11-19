#!/usr/bin/env python3
"""Check literature corpus identities, JSONL parity, files and page provenance.

The standard-library checks cover the generated data contract and cross-file
invariants. The supplied JSON Schema can also be used by external validators.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def require(condition: bool, message: str) -> None:
    """Stop validation with a useful error instead of a silent partial pass."""
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> object:
    """Load UTF-8 JSON and reject nonstandard NaN or Infinity values."""
    def invalid_constant(value: str) -> None:
        """Reject an invalid numeric constant encountered in a JSON record."""
        raise ValueError(f"Nonstandard JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid_constant)


def sha(data: bytes) -> str:
    """Return the SHA-256 of the original encoded bytes."""
    return hashlib.sha256(data).hexdigest()


def local_file(dataset: Path, relative: str) -> Path:
    """Resolve a required artifact while rejecting paths outside the dataset."""
    require(isinstance(relative, str), f"Invalid relative path: {relative}")
    path = (dataset / relative).resolve()
    require(path.is_relative_to(dataset), f"Path escapes dataset: {relative}")
    require(path.is_file(), f"Missing artifact: {relative}")
    return path


def validate(dataset: Path, workspace: Path | None) -> dict:
    """Validate every record and optionally compare against original OCR/PDFs."""
    info = read_json(dataset / "dataset_info.json")
    report = read_json(dataset / "quality_report.json")
    index = read_json(dataset / "index.json")
    schema = read_json(dataset / "schema/paper.schema.json")
    records = {}
    for path in sorted((dataset / "json").glob("*.json")):
        row = read_json(path)
        pmid = row["pmid"]
        require(re.fullmatch(r"[0-9]+", pmid) is not None, f"Invalid PMID: {pmid}")
        require(pmid not in records, f"Duplicate PMID: {pmid}")
        require(path.stem == pmid, f"File/PMID mismatch: {path}")
        require(set(row) == set(schema["required"]), f"Record fields: {pmid}")
        require(row["schema_version"] == info["version"], f"Version: {pmid}")
        require(bool(row["title"]) and bool(row["abstract"]), f"Empty metadata: {pmid}")
        require(type(row["publication_year"]) is int, f"Publication year: {pmid}")
        require(type(row["full_text_available"]) is bool, f"Availability: {pmid}")
        require(row["annotation_status"] == "not_causal_ground_truth", f"Labels: {pmid}")
        require(local_file(dataset, row["files"]["json"]) == path, f"JSON link: {pmid}")
        abstract = local_file(dataset, row["files"]["abstract_txt"]).read_bytes()
        require(abstract == (row["abstract"] + "\n").encode("utf-8"), f"Abstract mismatch: {pmid}")
        if row["full_text_available"]:
            require(row["content_type"] == "ocr_full_text", f"Text type: {pmid}")
            text = row["text"]
            data = local_file(dataset, row["files"]["txt"]).read_bytes()
            require(data == text.encode("utf-8"), f"TXT/JSON mismatch: {pmid}")
            require(sha(data) == row["text_sha256"], f"Text digest: {pmid}")
            require(len(row["pages"]) == row["page_count"], f"Page count: {pmid}")
            cursor = 0
            for n, page in enumerate(row["pages"], 1):
                require(page["page_number"] == n, f"Page order: {pmid}")
                marker = ("\n\n" if n > 1 else "") + f"[Page {n}]\n"
                start = cursor + len(marker)
                require(text[cursor:start] == marker, f"Page marker: {pmid}/{n}")
                require(page["char_start"] == start, f"Page start: {pmid}/{n}")
                require(start < page["char_end"] < len(text), f"Page span: {pmid}/{n}")
                require(page["status"] == "ok", f"OCR page status: {pmid}/{n}")
                require(page["generation_finish_reason"] == "stop", f"OCR truncated: {pmid}/{n}")
                cursor = page["char_end"]
            require(text[cursor:] == "\n", f"Page assembly: {pmid}")
            require("<MERGE>" not in text, f"Residual layout marker: {pmid}")
            warning_pages = [p["page_number"] for p in row["pages"] if p["warnings"]]
            require(warning_pages == row["quality"]["pages_with_warnings"], f"Warning pages: {pmid}")
            for part in (*row["headings"], *row["tables"]):
                require(1 <= part["page_number"] <= row["page_count"], f"Invalid page reference: {pmid}")
            if workspace:
                source_path = workspace / row["provenance"]["original_ocr_json"]
                source_data = source_path.read_bytes()
                source = json.loads(source_data)
                require(sha(source_data) == row["provenance"]["original_ocr_json_sha256"], f"Source JSON digest: {pmid}")
                require(source["source"]["bibliography"]["pmid"] == pmid, f"Source PMID: {pmid}")
                for original, normalized in zip(source["pages"], row["pages"]):
                    expected = re.sub(r"(?m)^[ \t]*<MERGE>[ \t]*(?:\n|$)", "", original["text"])
                    actual = text[normalized["char_start"]:normalized["char_end"]]
                    require(actual == expected, f"Normalized source page: {pmid}/{original['page_number']}")
                pdf = workspace / row["provenance"]["original_pdf"]
                require(sha(pdf.read_bytes()) == row["provenance"]["original_pdf_sha256"], f"Source PDF digest: {pmid}")
                original_txt = workspace / row["provenance"]["original_ocr_txt"]
                require(sha(original_txt.read_bytes()) == row["provenance"]["original_ocr_txt_sha256"], f"Source TXT digest: {pmid}")
        else:
            require(row["content_type"] == "abstract_only", f"Missing text type: {pmid}")
            require(all(row[k] is None for k in ("text", "text_sha256", "page_count")), f"Invented full text: {pmid}")
            require(row["files"]["txt"] is None, f"Invented TXT path: {pmid}")
            require(not row["pages"] and not row["headings"] and not row["tables"], f"Invented content: {pmid}")
        records[pmid] = row
    with (dataset / "papers.jsonl").open(encoding="utf-8") as stream:
        combined = [json.loads(line) for line in stream]
    require(len(combined) == len(records), "JSONL record count")
    require(len({r["pmid"] for r in combined}) == len(records), "JSONL duplicate IDs")
    require(all(r == records[r["pmid"]] for r in combined), "JSONL differs from individual JSON")
    require([r["source_number"] for r in combined] == sorted(r["source_number"] for r in combined), "JSONL ordering")
    require(len(index) == len(records), "Index count")
    require({r["pmid"] for r in index} == set(records), "Index IDs")
    for entry in index:
        row = records[entry["pmid"]]
        require(entry["full_text_available"] == row["full_text_available"], f"Index status: {row['pmid']}")
        require(entry["page_count"] == row["page_count"], f"Index pages: {row['pmid']}")
        require(entry["text_characters"] == len(row["text"] or ""), f"Index length: {row['pmid']}")
    with (dataset / "index.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    require([r["pmid"] for r in csv_rows] == [r["pmid"] for r in index], "CSV index ordering")
    full = [r for r in records.values() if r["full_text_available"]]
    require({p.stem for p in (dataset / "txt").glob("*.txt")} == {r["pmid"] for r in full}, "TXT file IDs")
    require({p.stem for p in (dataset / "abstracts").glob("*.txt")} == set(records), "Abstract file IDs")
    counts = {
        "records": len(records), "full_text_records": len(full),
        "abstract_only_records": len(records) - len(full),
        "ocr_pages": sum(r["page_count"] for r in full),
        "ocr_table_blocks": sum(len(r["tables"]) for r in full),
        "warning_documents": sum(bool(r["quality"]["pages_with_warnings"]) for r in full),
        "warning_pages": sum(len(r["quality"]["pages_with_warnings"]) for r in full),
        "abstract_screened_records": sum(r["screening"] is not None for r in records.values()),
        "screened_with_full_text": sum(r["screening"] is not None for r in full),
        "removed_standalone_merge_markers": sum(r["quality"]["removed_standalone_merge_markers"] for r in full),
    }
    require(all(report[k] == v for k, v in counts.items()), "Quality-report totals")
    require(all(info[k] == counts[k] for k in ("records", "full_text_records", "abstract_only_records")), "Dataset-info totals")
    for snapshot in info["source_snapshots"]:
        data = local_file(dataset, snapshot["snapshot"]).read_bytes()
        require(sha(data) == snapshot["sha256"], f"Snapshot digest: {snapshot['snapshot']}")
        if workspace:
            require(data == (workspace / snapshot["workspace_path"]).read_bytes(), f"Original snapshot changed: {snapshot['snapshot']}")
    require(sha(Path(__file__).with_name("build.py").read_bytes()) == info["build_script_sha256"], "Build script changed")
    return {
        "status": "pass", "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_sources_checked": workspace is not None, **counts,
        "checks": [
            "Unique PMID and file correspondence", "TXT and JSON Unicode text equality",
            "JSONL and individual JSON equality", "Ordered, nonempty page spans",
            "Page warnings and aggregate counts", "Abstract-only status and null full text",
            "Text and metadata snapshot hashes", "Source-to-output text and original PDFs" if workspace else "Standalone dataset integrity",
        ],
    }


def main() -> None:
    """Validate the corpus and optionally save a machine-readable report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path.cwd() / "datasets/literature")
    parser.add_argument("--workspace", type=Path, help="Also verify source OCR, PDF and metadata.")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate(args.dataset.resolve(), args.workspace.resolve() if args.workspace else None)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

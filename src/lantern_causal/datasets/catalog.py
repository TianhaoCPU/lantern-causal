"""Streaming access to the literature reference corpus, distinct from task truth."""

import json
from pathlib import Path
from typing import Iterator


def iter_papers(path: Path | str, full_text_only: bool = False) -> Iterator[dict]:
    """Yield corpus records from a JSONL file or its containing dataset directory."""
    path = Path(path)
    if path.is_dir():
        path = path / "papers.jsonl"
    seen = set()
    with path.open(encoding="utf-8") as stream:
        for n, line in enumerate(stream, 1):
            record = json.loads(line)
            pmid = record["pmid"]
            if pmid in seen:
                raise ValueError(f"Duplicate PMID on JSONL line {n}: {pmid}")
            seen.add(pmid)
            if not full_text_only or record["full_text_available"]:
                yield record

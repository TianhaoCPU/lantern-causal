"""Offline entry points for reference experiments, corpus loading and validation."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .datasets.catalog import iter_papers
from .experiments import run_example


def main() -> None:
    """Dispatch explicit local actions without API calls or implicit data downloads."""
    parser = argparse.ArgumentParser(prog="lantern")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run an exact synthetic reference case.")
    demo.add_argument("--config", type=Path, required=True)
    demo.add_argument("--output", type=Path)
    pilot = commands.add_parser("pilot", help="Run the synthetic A/B/C missingness pilot.")
    pilot.add_argument("--config", type=Path, required=True)
    pilot.add_argument("--output", type=Path)
    corpus = commands.add_parser("corpus", help="Summarize the local reference corpus.")
    corpus.add_argument("--dataset", type=Path, required=True)
    validate = commands.add_parser("validate-corpus", help="Validate a local corpus.")
    validate.add_argument("--dataset", type=Path, required=True)
    validate.add_argument("--workspace", type=Path)
    validate.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "demo":
            result = run_example(json.loads(args.config.read_text(encoding="utf-8")))
        elif args.command == "pilot":
            from .pilot import run_pilot
            result = run_pilot(json.loads(args.config.read_text(encoding="utf-8")))
        elif args.command == "corpus":
            records = list(iter_papers(args.dataset))
            result = {
                "records": len(records),
                "full_text": sum(r["full_text_available"] for r in records),
                "abstract_only": sum(not r["full_text_available"] for r in records),
            }
        else:
            from .datasets.validate import validate as validate_dataset
            result = validate_dataset(
                args.dataset.resolve(), args.workspace.resolve() if args.workspace else None
            )
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.command in ("demo", "pilot") and args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"lantern: {exc}\n")

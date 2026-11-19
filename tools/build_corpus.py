#!/usr/bin/env python3
"""Rebuild the local literature dataset using an explicit external-asset config."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    """Resolve local paths and delegate to the installed dataset builder."""
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=Path, default=project / "configs/local.paths.json")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    local = json.loads(args.paths.read_text()) if args.paths.exists() else {}
    workspace = args.workspace or os.environ.get("LANTERN_ASSET_ROOT") or local.get("source_workspace")
    if not workspace:
        parser.error("Set --workspace, LANTERN_ASSET_ROOT, or source_workspace in the local paths file.")
    output = args.output or Path(local.get("literature_dataset", "datasets/literature"))
    if not output.is_absolute():
        output = project / output
    source = Path(workspace).expanduser()
    if not source.is_absolute():
        source = project / source
    command = [
        sys.executable, "-m", "lantern_causal.datasets.build",
        "--workspace", str(source.resolve()), "--output", str(output.resolve()),
    ]
    if args.replace_generated:
        command.append("--replace-generated")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()

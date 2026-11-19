"""Compatibility entry point for the original calibrated-proxy reference case."""

import json

from lantern_causal.experiments import run_example


if __name__ == "__main__":
    print(json.dumps(run_example({"schema_version": 1, "scenario": "proxy"}), indent=2))

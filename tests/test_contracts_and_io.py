"""Check candidate rejection, endpoint ties and the public offline entry point."""

from fractions import Fraction as F
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lantern_causal.datasets import iter_papers
from lantern_causal.llm import validate_proposals
from lantern_causal.planning import CandidateBounds, endpoint_priority


class ContractTests(unittest.TestCase):
    """Verify proposal format and evidence limits without making API calls."""

    def payload(self):
        """Provide a small input-grounded candidate for contract tests."""
        return {"status": "candidates", "candidates": [{
            "id": "g1", "role": "shared recording cause", "nodes": ["U", "R", "Y"],
            "edges": [["U", "R"], ["U", "Y"]],
            "evidence_quotes": ["recording depends on baseline status"],
        }]}

    def test_literal_evidence_is_required(self):
        data = self.payload()
        validate_proposals(data, "The recording depends on baseline status.")
        with self.assertRaises(ValueError):
            validate_proposals(data, "Unrelated input.")

    def test_cycle_is_rejected(self):
        data = self.payload()
        data["candidates"][0]["edges"].append(["R", "U"])
        with self.assertRaises(ValueError):
            validate_proposals(data, "recording depends on baseline status")

    def test_endpoint_ties_are_preserved_and_rejected_graphs_removed(self):
        states = [
            CandidateBounds("low1", F(-1), F(0), cost=2),
            CandidateBounds("low2", F(-1), F(0), cost=3),
            CandidateBounds("high", F(0), F(1), cost=1),
            CandidateBounds("middle", F(-1, 2), F(1, 2), cost=0.5),
            CandidateBounds("excluded", F(-2), F(2), incompatible=True),
        ]
        self.assertEqual(endpoint_priority(states), ["high", "low1", "low2", "middle"])

    def test_invalid_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            CandidateBounds("bad", F(0), F(1), cost=float("nan"))

    def test_streaming_reader_skips_abstracts_and_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "papers.jsonl"
            rows = [
                {"pmid": "1", "full_text_available": True},
                {"pmid": "2", "full_text_available": False},
            ]
            path.write_text("\n".join(map(json.dumps, rows)) + "\n")
            self.assertEqual([r["pmid"] for r in iter_papers(path, True)], ["1"])
            path.write_text(json.dumps(rows[0]) + "\n" + json.dumps(rows[0]) + "\n")
            with self.assertRaises(ValueError):
                list(iter_papers(path))

    def test_cli_works_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "bridge.json"
            output = Path(temp) / "result.json"
            config.write_text(json.dumps({"schema_version": 1, "scenario": "bridge"}))
            process = subprocess.run(
                [sys.executable, "-m", "lantern_causal", "demo", "--config", str(config),
                 "--output", str(output)], cwd=temp, text=True, capture_output=True, check=True,
            )
            self.assertEqual(json.loads(process.stdout), json.loads(output.read_text()))
            self.assertEqual(json.loads(output.read_text())["reference_rd"]["percentage_points"], 90.0)


if __name__ == "__main__":
    unittest.main()

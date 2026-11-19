"""Check graph dispatch, prompt boundaries and honest offline evaluation scores."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lantern_causal.blind import export_tasks, response_template, run_blind_evaluation
from lantern_causal.llm import inspect_missingness_proposals, resolve_missingness, rule_proposal, validate_proposals
from lantern_causal.llm.missingness import make_missingness_proposal
from lantern_causal.pilot import analyze_observed
from lantern_causal.recovery import ObservedRow


def _rows(cells):
    order = ((0, 0), (0, 1), (1, 0), (1, 1), (None, 0), (None, 1))
    return [ObservedRow(x, y, "c") for (x, y), count in zip(order, cells) for _ in range(count)]


class MissingnessDispatchTests(unittest.TestCase):
    def test_each_supported_graph_uses_its_own_formula(self):
        evidence = "The retrospective sampler has the described inputs."
        for family, cells in (("outcome_only", (3, 3, 1, 9, 12, 4)),
                              ("exposure_only", (3, 1, 3, 9, 10, 6))):
            proposal = make_missingness_proposal([family], evidence)
            result = resolve_missingness(proposal, evidence, analyze_observed(_rows(cells)))
            self.assertEqual(result["decision"], "point_estimate_under_candidate_graph")
            self.assertEqual(result["point_estimate"]["exact"], "1/2")

    def test_joint_unknown_and_ambiguous_graphs_do_not_claim_a_point(self):
        evidence = "Insufficient extraction details."
        analysis = analyze_observed(_rows((3, 1, 1, 3, 0, 0)))
        # Equal plug-in values, and even coincident empirical bounds, do not
        # establish a graph's general recoverability or resolve text ambiguity.
        for families, uncertain, decision in (
            (["joint"], False, "generally_not_point_identified"),
            (["outcome_only", "exposure_only"], False, "multiple_candidate_graphs"),
            (["outcome_only"], True, "insufficient_information"),
            ([], True, "insufficient_information"),
        ):
            result = resolve_missingness(make_missingness_proposal(families, evidence, uncertain=uncertain),
                                         evidence, analysis)
            self.assertEqual(result["decision"], decision)
            self.assertIsNone(result["point_estimate"])
            self.assertEqual(result["observation_gate_bounds"], analysis["observation_gate_bounds"])

    def test_unrecognized_graph_is_kept_without_assuming_a_recovery_formula(self):
        evidence = "The recording mechanism has a latent input."
        unsupported = {"id": "latent", "role": "unknown recording input", "nodes": ["U", "R"],
                       "edges": [["U", "R"]], "evidence_quotes": [evidence]}
        proposal = make_missingness_proposal(["outcome_only"], evidence)
        proposal["candidates"].append(unsupported)
        analysis = analyze_observed(_rows((3, 3, 1, 9, 12, 4)))
        result = resolve_missingness(proposal, evidence, analysis)
        self.assertEqual(result["decision"], "unsupported_graph")
        self.assertIsNone(result["point_estimate"])
        self.assertTrue(result["observation_gate_bounds"]["has_nonunique_witness"])
        # Seeing Y->R alone is not enough: the fixed scaffold must also match.
        proposal = make_missingness_proposal(["outcome_only"], evidence)
        proposal["candidates"][0]["edges"].remove(["C", "X"])
        self.assertEqual(inspect_missingness_proposals(proposal, evidence)["families"], [])

    def test_missing_support_does_not_become_a_zero_estimate(self):
        evidence = "The selector reads Y. It cannot read X."
        analysis = analyze_observed(_rows((1, 0, 1, 0, 0, 1)))
        result = resolve_missingness(rule_proposal(evidence), evidence, analysis)
        self.assertEqual(result["decision"], "insufficient_support")
        self.assertIsNone(result["point_estimate"])
        self.assertEqual(result["candidates"][0]["estimation_status"], "insufficient_support")

    def test_rule_retains_unknown_dependencies_and_does_not_parse_unrecognized_negation(self):
        evidence = "The selector reads Y. The log does not describe the X input."
        checked = inspect_missingness_proposals(rule_proposal(evidence), evidence)
        self.assertEqual(set(checked["families"]), {"outcome_only", "joint"})
        self.assertEqual(checked["status"], "insufficient_information")
        evidence = "The selector never reads X."
        self.assertEqual(len(inspect_missingness_proposals(rule_proposal(evidence), evidence)["families"]), 3)
        evidence = "The selector reads X. It cannot read X."
        self.assertEqual(rule_proposal(evidence), {"status": "insufficient_information", "candidates": []})

    def test_malformed_model_json_and_duplicate_graphs_are_rejected_cleanly(self):
        evidence = "Allowed evidence."
        valid = make_missingness_proposal(["outcome_only"], evidence)
        for bad in (None, [], {"status": [], "candidates": []},
                    {"status": "candidates", "candidates": [None]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_proposals(bad, evidence)
        for bad_edge in ([["nested"], "R"], [1, "R"], ["X"], ["unknown", "R"]):
            bad = deepcopy(valid)
            bad["candidates"][0]["edges"].append(bad_edge)
            with self.subTest(edge=bad_edge), self.assertRaises(ValueError):
                validate_proposals(bad, evidence)
        bad = deepcopy(valid)
        bad["candidates"][0]["edges"].append(["Y", "R"])
        with self.assertRaises(ValueError):
            validate_proposals(bad, evidence)
        bad = deepcopy(valid)
        duplicate = deepcopy(bad["candidates"][0])
        duplicate["id"] = "another_id"
        bad["candidates"].append(duplicate)
        with self.assertRaises(ValueError):
            inspect_missingness_proposals(bad, evidence)
        bad = deepcopy(valid)
        bad["candidates"][0]["evidence_quotes"] = ["   "]
        with self.assertRaises(ValueError):
            validate_proposals(bad, evidence)


class BlindEvaluationTests(unittest.TestCase):
    config = {"schema_version": 1, "seeds": [1]}

    def submission(self, factory):
        bundle = response_template()
        bundle["responses"] = [
            {"task_id": task["task_id"], "proposal": factory(task["extraction_process"])}
            for task in export_tasks()["tasks"]
        ]
        return bundle

    def test_export_allowlist_and_fingerprint_exclude_generator_and_scoring_answers(self):
        bundle = export_tasks()
        self.assertEqual(set(bundle), {"schema_version", "task_set", "instructions", "field_definitions",
                                       "target", "tasks", "task_bundle_sha256"})
        self.assertEqual(len(bundle["tasks"]), 9)
        for task in bundle["tasks"]:
            self.assertEqual(set(task), {"task_id", "extraction_process"})
            self.assertRegex(task["task_id"], r"^process_[0-9a-f]{12}$")
        text = json.dumps(bundle)
        for forbidden in ("reference_rd", "expected_families", "scoring", "39/400", "0.0975", "intercept", "seed"):
            self.assertNotIn(forbidden, text)
        fingerprint = bundle.pop("task_bundle_sha256")
        canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        self.assertEqual(fingerprint, hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(export_tasks()["task_bundle_sha256"], fingerprint)

    def test_development_rules_cover_tasks_and_external_rule_answers_are_not_called_llm_results(self):
        submission = self.submission(rule_proposal)
        report = run_blind_evaluation(self.config, submission)
        rules = report["summary"]["rules"]
        self.assertFalse(report["provider_called"])
        self.assertFalse(report["patient_data_used"])
        self.assertTrue(report["external_responses_supplied"])
        self.assertEqual(report["unique_masks"], 3)
        self.assertEqual(rules["text"]["tasks"], 9)
        self.assertEqual(rules["text"]["exact_candidate_sets"], 9)
        self.assertEqual(rules["text"]["ambiguous_tasks_with_all_alternatives"], 3)
        self.assertEqual(rules["numerical"]["task_mask_pairs"], 13)
        self.assertEqual(rules["numerical"]["point_estimates"], 4)
        self.assertEqual(rules["numerical"]["false_point_estimates_on_joint_selection"], 0)
        self.assertEqual(report["summary"]["submitted"], rules)
        self.assertEqual(report["summary"]["known_graph"]["numerical"]["point_estimates"], 8)
        self.assertEqual(report["summary"]["always_mar"]["numerical"]["false_point_estimates_on_joint_selection"], 5)

    def test_literal_citation_does_not_hide_semantically_wrong_unique_answers(self):
        # All answers quote real process text, but force the MAR graph even
        # when the process describes X dependence or unresolved alternatives.
        submission = self.submission(lambda text: make_missingness_proposal(["outcome_only"], text))
        report = run_blind_evaluation(self.config, submission)
        summary = report["summary"]["submitted"]
        self.assertEqual(summary["text"]["valid_literal_citations"], 9)
        self.assertEqual(summary["text"]["exact_candidate_sets"], 2)
        self.assertEqual(summary["text"]["overconfident_single_graphs_on_ambiguous_tasks"], 3)
        self.assertEqual(summary["numerical"]["point_estimates"], 13)
        self.assertEqual(summary["numerical"]["false_point_estimates_on_joint_selection"], 5)

    def test_missing_invalid_and_abstaining_answers_keep_denominators(self):
        submission = self.submission(lambda text: None)
        submission["responses"] = submission["responses"][:2]
        summary = run_blind_evaluation(self.config, submission)["summary"]["submitted"]
        self.assertEqual(summary["text"]["tasks"], 9)
        self.assertEqual(summary["text"]["invalid"], 2)
        self.assertEqual(summary["text"]["missing"], 7)
        self.assertEqual(summary["numerical"]["task_mask_pairs"], 13)
        self.assertGreater(summary["numerical"]["invalid_response_pairs"], 0)
        self.assertGreater(summary["numerical"]["missing_response_pairs"], 0)
        self.assertEqual(summary["numerical"]["point_estimates"], 0)
        self.assertIsNone(summary["numerical"]["mean_absolute_error_among_point_estimates"])
        abstaining = self.submission(lambda text: {"status": "insufficient_information", "candidates": []})
        summary = run_blind_evaluation(self.config, abstaining)["summary"]["submitted"]
        self.assertEqual(summary["text"]["valid"], 9)
        self.assertEqual(summary["text"]["exact_candidate_sets"], 0)
        self.assertEqual(summary["numerical"]["without_point_estimate"], 13)

    def test_bundle_mismatch_duplicate_unknown_ids_and_malformed_envelopes_fail_fast(self):
        valid = self.submission(rule_proposal)
        invalids = [[], {}, {**valid, "schema_version": True},
                    {**valid, "task_bundle_sha256": "different"},
                    {**valid, "responses": {}},
                    {**valid, "responses": [valid["responses"][0]] * 2},
                    {**valid, "responses": [{"task_id": "unknown", "proposal": {}}]},
                    {**valid, "responses": [{"task_id": [], "proposal": {}}]},
                    {**valid, "responses": [{"task_id": valid["responses"][0]["task_id"]}]},
                    {**valid, "unexpected": 1}]
        # None means no submission for the Python API; JSON null at the CLI
        # is rejected separately instead of silently skipping submitted scores.
        for bad in invalids:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                run_blind_evaluation(self.config, bad)

    def test_cli_exports_tasks_and_scores_partial_responses_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tasks, template, config, report = [root / name for name in ("tasks.json", "responses.json", "config.json", "report.json")]
            config.write_text(json.dumps(self.config), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, "-m", "lantern_causal", "blind-tasks", "--output", str(tasks),
                 "--response-template", str(template)], cwd=temp, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(process.stdout), json.loads(tasks.read_text()))
            process = subprocess.run(
                [sys.executable, "-m", "lantern_causal", "blind-eval", "--config", str(config),
                 "--responses", str(template), "--output", str(report)],
                cwd=temp, text=True, capture_output=True, check=True)
            output = json.loads(report.read_text())
            self.assertEqual(json.loads(process.stdout), output)
            self.assertEqual(output["summary"]["submitted"]["text"]["missing"], 9)
            template.write_text("null", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, "-m", "lantern_causal", "blind-eval", "--config", str(config),
                 "--responses", str(template)], cwd=temp, text=True, capture_output=True)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn("Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main()

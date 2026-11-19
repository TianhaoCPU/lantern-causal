"""Frozen synthetic process tasks and an offline, answer-separated evaluator.

Only export_tasks() produces model input. This module's fixtures and evaluation
reports contain answers and are not held-out benchmarks or blinded inputs.
"""

from fractions import Fraction
import hashlib
from importlib.resources import files
import json
import math

from .experiments import rd_value
from .llm.missingness import (
    inspect_missingness_proposals, resolve_missingness, rule_proposal,
)
from .pilot import run_pilot


_SCENARIOS = {"outcome_only": "A", "exposure_only": "B", "joint": "C"}
_PREFIX = "A retrospective selector samples artificial records within age-sex strata. "
_SUFFIX = " Rejected records retain Y and C, with X masked."
_CASES = (
    (_PREFIX + "The selector reads Y. It cannot read X." + _SUFFIX, ("outcome_only",)),
    (_PREFIX + "For the selection decision it uses Y. X is unavailable until the decision is complete."
     + _SUFFIX, ("outcome_only",)),
    (_PREFIX + "The selector reads X. It cannot read Y." + _SUFFIX, ("exposure_only",)),
    (_PREFIX + "For the selection decision it uses X. Y is unavailable until the decision is complete."
     + _SUFFIX, ("exposure_only",)),
    (_PREFIX + "The selector reads X. The selector reads Y." + _SUFFIX, ("joint",)),
    (_PREFIX + "For the selection decision it uses X. For the selection decision it uses Y."
     + _SUFFIX, ("joint",)),
    (_PREFIX + "The archived log does not identify whether X, Y or both were supplied to the selector."
     + _SUFFIX, ("outcome_only", "exposure_only", "joint")),
    (_PREFIX + "The selector reads Y. The log does not say whether X was also supplied."
     + _SUFFIX, ("outcome_only", "joint")),
    (_PREFIX + "The selector reads X. The log does not say whether Y was also supplied."
     + _SUFFIX, ("exposure_only", "joint")),
)


def _sha256(value) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cases() -> dict:
    return {"process_" + _sha256(text)[:12]: (text, families) for text, families in _CASES}


def export_tasks() -> dict:
    """Allowlist model-visible content; do not copy fields from pilot reports."""
    content = {
        "schema_version": 1, "task_set": "synthetic_missingness_process_v1",
        "instructions": files("lantern_causal.llm").joinpath("missingness_prompt.md").read_text(encoding="utf-8"),
        "field_definitions": {
            "C": "Fully observed age-sex stratum of an artificial record.",
            "X": "Binary artificial laboratory group; masked when R=0.",
            "Y": "Fully observed binary artificial follow-up outcome, adjudicated before extraction.",
            "R": "Retrospective retention indicator: X is readable exactly when R=1.",
        },
        "target": "sum_c P(C=c) * [P(Y=1|X=1,C=c) - P(Y=1|X=0,C=c)]",
        "tasks": [{"task_id": identifier, "extraction_process": text}
                  for identifier, (text, _) in sorted(_cases().items())],
    }
    return {**content, "task_bundle_sha256": _sha256(content)}


def response_template() -> dict:
    """Return an empty response envelope bound to the current public tasks."""
    return {"schema_version": 1, "task_bundle_sha256": export_tasks()["task_bundle_sha256"],
            "responses": []}


def _submission_answers(submission: dict, bundle: dict) -> dict:
    if (not isinstance(submission, dict) or
        set(submission) != {"schema_version", "task_bundle_sha256", "responses"} or
        type(submission["schema_version"]) is not int or submission["schema_version"] != 1):
        raise ValueError("Expected a response envelope with schema_version=1, task_bundle_sha256 and responses.")
    if submission["task_bundle_sha256"] != bundle["task_bundle_sha256"]:
        raise ValueError("Responses do not match the frozen task bundle fingerprint.")
    if not isinstance(submission["responses"], list):
        raise ValueError("Responses must be a list.")
    known_ids = {task["task_id"] for task in bundle["tasks"]}
    answers = {}
    for response in submission["responses"]:
        if not isinstance(response, dict) or set(response) != {"task_id", "proposal"}:
            raise ValueError("Each response needs exactly task_id and proposal.")
        identifier = response["task_id"]
        if not isinstance(identifier, str) or identifier not in known_ids or identifier in answers:
            raise ValueError("Response task IDs must be known and unique.")
        answers[identifier] = response["proposal"]
    _sha256(submission)  # Reject non-JSON numbers before any experiment is run.
    return answers


def _assess(answers: dict, identifier: str, evidence: str, expected: tuple) -> dict:
    result = {"status": "missing", "proposed_families": [], "candidate_set_exact": False,
              "candidate_recall": 0.0, "literal_quotes_valid": None,
              "overconfident_single_graph": False, "uncertainty_status_correct": False}
    if identifier not in answers:
        return result
    try:
        checked = inspect_missingness_proposals(answers[identifier], evidence)
    except ValueError as exc:
        return {**result, "status": "invalid", "reason": str(exc)}
    proposed = set(checked["families"])
    unsupported = checked["unsupported_candidate_ids"]
    return {**result, "status": "valid", "proposed_families": checked["families"],
            "literal_quotes_valid": True, "unsupported_candidate_ids": unsupported,
            "candidate_set_exact": not unsupported and proposed == set(expected),
            "candidate_recall": len(proposed & set(expected)) / len(expected),
            "overconfident_single_graph": (len(expected) > 1 and checked["status"] == "candidates"
                                           and len(checked["candidates"]) == 1),
            "uncertainty_status_correct": checked["status"] == (
                "insufficient_information" if len(expected) > 1 else "candidates")}


def _text_summary(assessments: list[dict], ambiguous: list[bool]) -> dict:
    total = len(assessments)
    return {
        "tasks": total,
        "valid": sum(a["status"] == "valid" for a in assessments),
        "missing": sum(a["status"] == "missing" for a in assessments),
        "invalid": sum(a["status"] == "invalid" for a in assessments),
        "unsupported": sum(bool(a.get("unsupported_candidate_ids")) for a in assessments),
        "exact_candidate_sets": sum(a["candidate_set_exact"] for a in assessments),
        "exact_candidate_set_rate": sum(a["candidate_set_exact"] for a in assessments) / total,
        "mean_candidate_recall": sum(a["candidate_recall"] for a in assessments) / total,
        "valid_literal_citations": sum(a["literal_quotes_valid"] is True for a in assessments),
        "correct_uncertainty_status": sum(a["uncertainty_status_correct"] for a in assessments),
        "ambiguous_tasks": sum(ambiguous),
        "ambiguous_tasks_with_all_alternatives": sum(
            a["candidate_recall"] == 1 for a, flag in zip(assessments, ambiguous) if flag),
        "overconfident_single_graphs_on_ambiguous_tasks": sum(a["overconfident_single_graph"] for a in assessments),
    }


def _numeric_summary(runs: list[dict], method: str) -> dict:
    values = [run["methods"][method] for run in runs]
    errors = [Fraction(value["absolute_error"]["exact"]) for value in values
              if value["absolute_error"] is not None]
    mean_error = math.fsum(float(value) for value in errors) / len(errors) if errors else None
    return {
        "task_mask_pairs": len(runs), "point_estimates": len(errors),
        "without_point_estimate": len(runs) - len(errors),
        "support_failures": sum(v["decision"] == "insufficient_support" for v in values),
        "missing_response_pairs": sum(v["decision"] == "missing_response" for v in values),
        "invalid_response_pairs": sum(v["decision"] == "invalid_response" for v in values),
        "joint_selection_pairs": sum(run["scenario"] == "C" for run in runs),
        "false_point_estimates_on_joint_selection": sum(
            run["scenario"] == "C" and value["point_estimate"] is not None
            for run, value in zip(runs, values)),
        "mean_absolute_error_among_point_estimates": (
            {"probability_difference": mean_error, "percentage_points": 100 * mean_error}
            if mean_error is not None else None),
    }


def run_blind_evaluation(config: dict, submission: dict | None = None) -> dict:
    """Score text once per task and formulas on paired masks; make no API calls."""
    bundle = export_tasks()
    answers = {"rules": {task["task_id"]: rule_proposal(task["extraction_process"])
                         for task in bundle["tasks"]}}
    if submission is not None:
        answers["submitted"] = _submission_answers(submission, bundle)
    pilot = run_pilot(config)
    reference = Fraction(pilot["reference_rd"]["exact"])
    masks = {(run["scenario"], run["seed"]): run for run in pilot["runs"]}
    tasks, numerical_runs = [], []
    for identifier, (evidence, expected) in sorted(_cases().items()):
        assessments = {name: _assess(proposals, identifier, evidence, expected)
                       for name, proposals in answers.items()}
        tasks.append({"task_id": identifier, "expected_families": list(expected),
                      "ambiguous": len(expected) > 1, "assessments": assessments,
                      "responses": {name: proposals.get(identifier) for name, proposals in answers.items()}})
        for family in expected:
            scenario = _SCENARIOS[family]
            for seed in pilot["config"]["seeds"]:
                mask = masks[scenario, seed]
                analysis = mask["analysis"]
                methods = {}
                for name, proposals in answers.items():
                    validity = assessments[name]["status"]
                    methods[name] = (resolve_missingness(proposals[identifier], evidence, analysis)
                                     if validity == "valid" else
                                     {"decision": validity + "_response", "point_estimate": None})
                oracle = mask["known_graph_baseline"]
                methods["known_graph"] = {
                    "decision": ("generally_not_point_identified" if scenario == "C" else
                                 "point_estimate_under_candidate_graph" if oracle["estimation_status"] == "ok"
                                 else "insufficient_support"),
                    "point_estimate": oracle["point_estimate"],
                }
                for name, estimator in (("always_mar", "assume_r_independent_x_given_y_c"),
                                        ("complete_case", "assume_r_independent_y_given_x_c")):
                    value = analysis["estimators"][estimator]
                    methods[name] = {"decision": "point_estimate" if value["status"] == "ok" else value["status"],
                                     "point_estimate": value.get("rd")}
                scored = {}
                for name, value in methods.items():
                    point = value["point_estimate"]
                    scored[name] = {
                        "decision": value["decision"], "point_estimate": point,
                        "absolute_error": rd_value(abs(Fraction(point["exact"]) - reference)) if point else None,
                    }
                numerical_runs.append({"task_id": identifier, "scenario": scenario, "seed": seed,
                                       "mask_key": f"{scenario}:{seed}", "methods": scored})
    summaries = {}
    ambiguous = [task["ambiguous"] for task in tasks]
    for name in (*answers, "known_graph", "always_mar", "complete_case"):
        summaries[name] = {"numerical": _numeric_summary(numerical_runs, name)}
        if name in answers:
            summaries[name]["text"] = _text_summary([task["assessments"][name] for task in tasks], ambiguous)
    return {
        "project": "LANTERN-Causal", "experiment": "offline_synthetic_process_evaluation",
        "schema_version": 1, "task_bundle_sha256": bundle["task_bundle_sha256"],
        "submission_sha256": _sha256(submission) if submission is not None else None,
        "config": pilot["config"], "config_sha256": pilot["config_sha256"],
        "provider_called": False, "patient_data_used": False,
        "external_responses_supplied": submission is not None,
        "rules_version": "explicit_read_tokens_v1", "reference_rd": pilot["reference_rd"],
        "unique_masks": len(masks), "summary": summaries, "tasks": tasks,
        "mask_analyses": [{"mask_key": f"{s}:{seed}", "analysis": mask["analysis"]}
                          for (s, seed), mask in masks.items()],
        "numerical_runs": numerical_runs,
        "interpretation": (
            "Scoring-only synthetic development fixtures, not held-out clinical or LLM results. "
            "Text tasks are scored once; task-mask pairs reuse masks and are not independent studies. "
            "MAE is conditional on reporting a point estimate; missing and invalid answers remain in denominators. "
            "Observation-gate bounds and witnesses do not impose the proposed graph's conditional independences. "
            "Literal citations check substrings, not semantic entailment. External model provenance is unverified."
        ),
    }

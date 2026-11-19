"""Map proposals in a fixed three-graph family to named recovery formulas.

This adapter checks graph syntax, not evidence entailment or clinical truth.
The saturated C,X,Y scaffold is a factorization convention. Only the arrows
into the retrospective recording indicator R vary across these examples.
"""

import re

from .contracts import validate_proposals


BASE_EDGES = (("C", "X"), ("C", "Y"), ("X", "Y"), ("C", "R"))
FAMILY_PARENTS = {"outcome_only": ("Y",), "exposure_only": ("X",),
                  "joint": ("X", "Y")}
_ESTIMATORS = {"outcome_only": "assume_r_independent_x_given_y_c",
               "exposure_only": "assume_r_independent_y_given_x_c"}


def inspect_missingness_proposals(payload: dict, evidence: str) -> dict:
    """Validate literal citations and recognize only exact supported graphs."""
    validate_proposals(payload, evidence)
    candidates, seen = [], set()
    for candidate in payload["candidates"]:
        edges = {tuple(edge) for edge in candidate["edges"]}
        family = None
        if set(candidate["nodes"]) == {"C", "X", "Y", "R"}:
            for name, parents in FAMILY_PARENTS.items():
                if edges == set(BASE_EDGES) | {(node, "R") for node in parents}:
                    family = name
                    break
        if family is not None:
            if family in seen:
                raise ValueError("Do not repeat the same missingness graph under different IDs.")
            seen.add(family)
        candidates.append({"id": candidate["id"], "family": family})
    return {"status": payload["status"], "candidates": candidates,
            "families": sorted(seen),
            "unsupported_candidate_ids": [c["id"] for c in candidates if c["family"] is None]}


def resolve_missingness(payload: dict, evidence: str, analysis: dict) -> dict:
    """Dispatch using only proposals, process text and analyze_observed output.

    Unknown or multiple graphs retain the observation-gate bounds. Their
    individual plug-in estimates are never treated as sharp cross-graph bounds.
    """
    checked = inspect_missingness_proposals(payload, evidence)
    candidates = []
    for candidate in checked["candidates"]:
        result = dict(candidate)
        family = candidate["family"]
        if family in _ESTIMATORS:
            method = _ESTIMATORS[family]
            estimate = analysis["estimators"][method]
            result.update({"identification": "point_identified_under_graph_and_support",
                           "estimator": method, "estimation_status": estimate["status"],
                           "point_estimate": estimate.get("rd")})
        else:
            result.update({"identification": ("generally_not_point_identified" if family == "joint"
                                               else "unsupported_graph"),
                           "point_estimate": None})
        candidates.append(result)

    point = None
    if checked["unsupported_candidate_ids"]:
        decision = "unsupported_graph"
    elif checked["status"] == "insufficient_information" or not candidates:
        decision = "insufficient_information"
    elif len(candidates) > 1:
        decision = "multiple_candidate_graphs"
    elif candidates[0]["family"] == "joint":
        decision = "generally_not_point_identified"
    elif candidates[0]["estimation_status"] != "ok":
        decision = "insufficient_support"
    else:
        decision = "point_estimate_under_candidate_graph"
        point = candidates[0]["point_estimate"]
    return {"decision": decision, "point_estimate": point, "candidates": candidates,
            "observation_gate_bounds": analysis["observation_gate_bounds"],
            "scope": "Conditional on supplied proposals; literal citations do not verify their meaning."}


def make_missingness_proposal(families: list[str], evidence: str, *, uncertain: bool = False) -> dict:
    """Construct a cited proposal for the transparent rule and oracle baselines."""
    return {
        "status": "insufficient_information" if uncertain else "candidates",
        "candidates": [
            {"id": family, "role": f"Retrospective recording: {family}",
             "nodes": ["C", "X", "Y", "R"],
             "edges": [list(edge) for edge in BASE_EDGES]
                      + [[node, "R"] for node in FAMILY_PARENTS[family]],
             "evidence_quotes": [evidence]}
            for family in families
        ],
    }


def rule_proposal(evidence: str) -> dict:
    """Read a frozen toy grammar; unrecognized dependencies stay possible.

    This deliberately small baseline recognizes complete sentences in two
    declared templates. It never consults task IDs or gold labels.
    """
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("Rule input must be nonempty process text.")
    sentences = re.split(r"(?<=[.!?])\s+", evidence.strip())
    known = {}
    for node in ("X", "Y"):
        positive = any(re.fullmatch(rf"(?:The selector reads|For the selection decision it uses) {node}\.",
                                    sentence, re.IGNORECASE) for sentence in sentences)
        negative = any(re.fullmatch(rf"(?:It cannot read {node}|{node} is unavailable until the decision is complete)\.",
                                    sentence, re.IGNORECASE) for sentence in sentences)
        if positive and negative:
            return make_missingness_proposal([], evidence, uncertain=True)
        known[node] = True if positive else False if negative else None
    families = [name for name, parents in FAMILY_PARENTS.items()
                if all(present is None or (node in parents) == present
                       for node, present in known.items())]
    return make_missingness_proposal(families, evidence, uncertain=len(families) != 1)

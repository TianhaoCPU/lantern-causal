"""Reproducible, synthetic-only A/B/C missingness pilot and scorer.

The analysis functions receive only masked rows. The runner retains complete
synthetic rows for masking and scoring and must not be used as a blinded prompt.
"""

from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import random

from .experiments import rd_value
from .recovery.stratified import (
    FullRow, ObservedRow, SupportError, empirical_bounds, standardized_mar,
    standardized_reference, standardized_visible,
)


# Fixed artificial counts indexed by (X=0,Y=0), (0,1), (1,0), (1,1).
# They are examples, not estimates or parameters from MIMIC.
_FIXTURE = {
    "under65_male": (120, 30, 70, 30),
    "under65_female": (105, 20, 90, 35),
    "65plus_male": (90, 60, 55, 45),
    "65plus_female": (85, 40, 70, 55),
}
_COEFFICIENTS = {"A": (0.0, math.log(2)), "B": (math.log(2), 0.0),
                 "C": (math.log(2), math.log(2))}
_STRATUM_EFFECT = {"under65_male": 0.0, "under65_female": 0.2,
                   "65plus_male": 0.4, "65plus_female": 0.6}


def synthetic_reference() -> list[FullRow]:
    """Return the versioned, complete artificial reference cohort in fixed order."""
    rows = []
    for c, cell_counts in _FIXTURE.items():
        for (x, y), count in zip(((0, 0), (0, 1), (1, 0), (1, 1)), cell_counts):
            rows.extend(FullRow(x, y, c) for _ in range(count))
    return rows


def _linear_part(row: FullRow, scenario: str) -> float:
    bx, by = _COEFFICIENTS[scenario]
    return _STRATUM_EFFECT[row.c] + bx * row.x + by * row.y


def _logistic(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


def _intercept(rows: list[FullRow], scenario: str, missing_rate: float) -> float:
    """Calibrate average expected missingness, never the realized count."""
    linear = [_linear_part(row, scenario) for row in rows]
    lower, upper = -100.0, 100.0
    for _ in range(100):
        middle = (lower + upper) / 2
        visibility = sum(_logistic(middle + value) for value in linear) / len(linear)
        if visibility < 1 - missing_rate:
            lower = middle
        else:
            upper = middle
    return (lower + upper) / 2


def mask_reference(
    rows: list[FullRow], scenario: str, seed: int, missing_rate: float = 0.3,
) -> tuple[list[ObservedRow], float]:
    """Generate one analysis view with paired uniforms and no support-based retries."""
    if scenario not in _COEFFICIENTS:
        raise ValueError("Scenario must be A, B or C.")
    if not rows or any(not isinstance(row, FullRow) for row in rows):
        raise ValueError("The masking generator requires nonempty FullRow data.")
    if any(row.c not in _STRATUM_EFFECT for row in rows):
        raise ValueError("The synthetic generator requires the four predefined strata.")
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer.")
    if isinstance(missing_rate, bool) or not isinstance(missing_rate, (int, float)) or not 0 < missing_rate < 1:
        raise ValueError("The expected missing rate must be strictly between 0 and 1.")
    alpha = _intercept(rows, scenario, missing_rate)
    rng = random.Random(seed)
    observed = []
    for row in rows:
        visible = rng.random() < _logistic(alpha + _linear_part(row, scenario))
        observed.append(ObservedRow(row.x if visible else None, row.y, row.c))
    return observed, alpha


def _observed_cells(rows: list[ObservedRow]) -> list[dict]:
    counts = Counter((row.c, row.x, row.y) for row in rows)
    cells = []
    for c in sorted({row.c for row in rows}):
        cells.append({
            "stratum": c,
            "visible_x0_y0": counts[c, 0, 0], "visible_x0_y1": counts[c, 0, 1],
            "visible_x1_y0": counts[c, 1, 0], "visible_x1_y1": counts[c, 1, 1],
            "missing_y0": counts[c, None, 0], "missing_y1": counts[c, None, 1],
        })
    return cells


def _estimate(fn, rows: list[ObservedRow]) -> dict:
    try:
        return {"status": "ok", "rd": rd_value(fn(rows))}
    except SupportError as exc:
        return {"status": "insufficient_support", "reason": str(exc)}


def _allocation_rows(allocation: dict[tuple[str, int], int]) -> list[dict]:
    return [
        {"stratum": c, "missing_y0_assigned_x1": allocation[c, 0],
         "missing_y1_assigned_x1": allocation[c, 1]}
        for c in sorted({c for c, _ in allocation})
    ]


def analyze_observed(rows: list[ObservedRow]) -> dict:
    """Analyze only X*,Y,C; estimates explicitly require their named assumptions."""
    # Both functions validate the input and reject an empty observation view.
    mar = _estimate(standardized_mar, rows)
    visible = _estimate(standardized_visible, rows)
    try:
        bounds = empirical_bounds(rows)
        bound_report = {
            "status": "ok", "lower": rd_value(bounds.lower), "upper": rd_value(bounds.upper),
            "width": rd_value(bounds.upper - bounds.lower),
            "has_nonunique_witness": bounds.lower != bounds.upper,
            "lower_witness": _allocation_rows(bounds.lower_allocation),
            "upper_witness": _allocation_rows(bounds.upper_allocation),
        }
    except SupportError as exc:
        bound_report = {"status": "insufficient_support", "reason": str(exc)}
    return {
        "observed_counts": _observed_cells(rows),
        "estimators": {"assume_r_independent_x_given_y_c": mar,
                       "assume_r_independent_y_given_x_c": visible},
        "observation_gate_bounds": bound_report,
    }


def _graph_result(scenario: str, analysis: dict) -> dict:
    """Apply a supplied graph as an oracle baseline, without inferring it."""
    if scenario == "C":
        bounds = analysis["observation_gate_bounds"]
        return {
            "identification": "generally_not_point_identified",
            "point_estimate": None,
            "empirical_status": (
                "insufficient_support" if bounds["status"] != "ok" else
                "nonunique_witness" if bounds["has_nonunique_witness"] else
                "coincident_empirical_endpoints"
            ),
        }
    method = ("assume_r_independent_x_given_y_c" if scenario == "A"
              else "assume_r_independent_y_given_x_c")
    value = analysis["estimators"][method]
    return {"identification": "point_identified_under_graph_and_support",
            "estimator": method, "estimation_status": value["status"],
            "point_estimate": value.get("rd")}


def _score(analysis: dict, reference: Fraction) -> dict:
    estimates = {}
    for name, value in analysis["estimators"].items():
        if value["status"] == "ok":
            estimates[name] = rd_value(abs(Fraction(value["rd"]["exact"]) - reference))
        else:
            estimates[name] = None
    bounds = analysis["observation_gate_bounds"]
    inside = None
    if bounds["status"] == "ok":
        inside = Fraction(bounds["lower"]["exact"]) <= reference <= Fraction(bounds["upper"]["exact"])
    return {"absolute_errors": estimates, "reference_in_bounds": inside}


def _mean_rd(values: list[Fraction]) -> dict | None:
    """Return a decimal summary without huge cross-run rational denominators."""
    if not values:
        return None
    mean = math.fsum(float(value) for value in values) / len(values)
    return {"probability_difference": mean, "percentage_points": 100 * mean}


def run_pilot(config: dict) -> dict:
    """Run paired synthetic masks; expose results and scoring as distinct fields."""
    if not isinstance(config, dict):
        raise ValueError("Pilot configuration must be an object.")
    unknown = set(config) - {"schema_version", "seeds", "expected_missing_rate"}
    if unknown:
        raise ValueError(f"Unknown pilot configuration keys: {sorted(unknown)}")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("Expected pilot schema_version=1.")
    seeds = config.get("seeds", list(range(1, 21)))
    if (not isinstance(seeds, list) or not seeds or
        any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds)):
        raise ValueError("Seeds must be a nonempty list of unique nonnegative integers.")
    missing_rate = config.get("expected_missing_rate", 0.3)
    effective_config = {"schema_version": 1, "seeds": seeds, "expected_missing_rate": missing_rate}
    full = synthetic_reference()
    reference = standardized_reference(full)
    runs, summary = [], {}
    for scenario in _COEFFICIENTS:
        scenario_runs = []
        for seed in seeds:
            observed, alpha = mask_reference(full, scenario, seed, missing_rate)
            analysis = analyze_observed(observed)
            scored = _score(analysis, reference)
            result = {"scenario": scenario, "seed": seed, "intercept": alpha,
                      "actual_missing_rate": sum(row.x is None for row in observed) / len(observed),
                      "analysis": analysis, "known_graph_baseline": _graph_result(scenario, analysis),
                      "scoring": scored}
            runs.append(result)
            scenario_runs.append(result)
        methods = {}
        for method in ("assume_r_independent_x_given_y_c", "assume_r_independent_y_given_x_c"):
            errors = [Fraction(run["scoring"]["absolute_errors"][method]["exact"])
                      for run in scenario_runs if run["scoring"]["absolute_errors"][method] is not None]
            methods[method] = {"successful": len(errors), "failed": len(seeds) - len(errors),
                               "mean_absolute_error": _mean_rd(errors)}
        paired_differences = []
        for run in scenario_runs:
            errors = run["scoring"]["absolute_errors"]
            mar = errors["assume_r_independent_x_given_y_c"]
            visible = errors["assume_r_independent_y_given_x_c"]
            if mar is not None and visible is not None:
                paired_differences.append(Fraction(mar["exact"]) - Fraction(visible["exact"]))
        widths = [Fraction(run["analysis"]["observation_gate_bounds"]["width"]["exact"])
                  for run in scenario_runs if run["analysis"]["observation_gate_bounds"]["status"] == "ok"]
        summary[scenario] = {
            "repetitions": len(seeds), "methods": methods,
            "bounds_computed": sum(run["scoring"]["reference_in_bounds"] is not None for run in scenario_runs),
            "reference_in_bounds": sum(run["scoring"]["reference_in_bounds"] is True for run in scenario_runs),
            "mean_actual_missing_rate": sum(run["actual_missing_rate"] for run in scenario_runs) / len(seeds),
            "mean_bounds_width": _mean_rd(widths),
            "nonunique_witness_runs": sum(
                run["analysis"]["observation_gate_bounds"].get("has_nonunique_witness", False)
                for run in scenario_runs
            ),
            "paired_absolute_error_comparison": {
                "pairs": len(paired_differences),
                "contrast": "MAR absolute error minus standardized visible-case absolute error",
                "mean_difference": _mean_rd(paired_differences),
            },
        }
    return {
        "project": "LANTERN-Causal", "experiment": "synthetic_missingness_pilot",
        "schema_version": 1, "config": effective_config,
        "config_sha256": hashlib.sha256(
            json.dumps(effective_config, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "fixture": "four_strata_binary_v1", "paired_uniforms_across_scenarios": True,
        "patient_data_used": False, "llm_executed": False,
        "cohort_size": len(full), "reference_rd": rd_value(reference),
        "interpretation": (
            "Synthetic fixed-cohort evaluation. Estimates require the named graph assumptions; "
            "bounds are finite-cohort identification bounds, not confidence intervals. "
            "Scoring contains the synthetic reference and should not be supplied to blinded analysis."
        ),
        "summary": summary, "runs": runs,
    }

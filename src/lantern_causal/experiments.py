"""Run exact reference experiments and serialize their assumptions and outputs."""

from fractions import Fraction
import hashlib
import json

from .distributions import marginal_xy, visible_xy
from .inflation import cut_triangle_certificate
from .recovery import recover_with_calibrated_proxy, risk_difference, unrestricted_bounds
from .synthetic import make_case


def rd_value(value: Fraction) -> dict:
    """Expose both probability difference and percentage points without ambiguity."""
    return {"probability_difference": float(value),
            "percentage_points": float(100 * value), "exact": str(value)}


def run_example(config: dict) -> dict:
    """Run a synthetic configuration; no LLM or patient data is accessed."""
    if config.get("schema_version") != 1:
        raise ValueError("Expected experiment schema_version=1.")
    name = config["scenario"]
    error = Fraction(str(config.get("flip_error", "1/20")))
    exposure_error = Fraction(str(config.get("exposure_error", "1/5")))
    case = make_case(name, error, exposure_error)
    certificate = cut_triangle_certificate(case.observed)
    reference = risk_difference(marginal_xy(case.full))
    visible = risk_difference(visible_xy(case.observed))
    rows = [
        {"x_visible": x, "y": y, "r": r, "z": z,
         "probability": float(p), "exact": str(p)}
        for (x, y, r, z), p in sorted(
            case.observed.items(), key=lambda item: tuple(-1 if v is None else v for v in item[0])
        )
    ]
    result = {
        "project": "LANTERN-Causal", "scenario": name,
        "status": "exact_synthetic_reference", "llm_executed": False,
        "patient_data_used": False, "config": config,
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "reference_rd": rd_value(reference),
        "complete_case_rd": rd_value(visible),
        "triangle_certificate": certificate.as_dict(),
        "observable_distribution": rows,
    }
    if name == "proxy":
        recovered = recover_with_calibrated_proxy(case.observed, error)
        result.update({
            "recovered_rd": rd_value(risk_difference(recovered)),
            "extra_information": "Known symmetric proxy error, independent proxy errors, and recording conditional independence.",
            "recovered_full_xy_equals_reference": recovered == marginal_xy(case.full),
        })
    else:
        lower, upper = unrestricted_bounds(case.observed)
        result.update({
            "before_inflation_outer_bounds": [rd_value(lower), rd_value(upper)],
            "after_inflation_outer_bounds": [
                rd_value(visible if certificate.incompatible else lower),
                rd_value(visible if certificate.incompatible else upper),
            ],
            "extra_information": None,
            "scope": "Only the prespecified common-upstream and independent-pair triangle candidates; exact data.",
            "remaining_graph_assumption": "R independent of Y conditional on X, plus observed support.",
        })
    return result

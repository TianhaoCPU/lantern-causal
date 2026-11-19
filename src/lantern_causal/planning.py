"""A transparent target-endpoint ordering utility, not a validated search solver."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True)
class CandidateBounds:
    """Current conservative bounds, estimated next-test cost and rejection status."""

    graph_id: str
    lower: Fraction
    upper: Fraction
    cost: float = 1.0
    incompatible: bool = False

    def __post_init__(self) -> None:
        """Reject malformed bounds or nonpositive/nonfinite costs."""
        import math
        if self.lower > self.upper or not math.isfinite(self.cost) or self.cost <= 0:
            raise ValueError("Bounds must be ordered and test cost finite and positive.")


def endpoint_priority(candidates: Iterable[CandidateBounds]) -> list[str]:
    """Prioritize all retained graphs sustaining either envelope endpoint.

    Tied endpoints all stay in the queue. Excluded graphs do not participate;
    nonendpoint graphs remain after endpoint graphs. This utility only orders
    supplied states and makes no claim of optimality or statistical validity.
    """
    retained = [g for g in candidates if not g.incompatible]
    if len({g.graph_id for g in retained}) != len(retained):
        raise ValueError("Retained graph IDs must be unique.")
    if not retained:
        return []
    lower = min(g.lower for g in retained)
    upper = max(g.upper for g in retained)
    return [
        g.graph_id for g in sorted(
            retained,
            key=lambda g: (not (g.lower == lower or g.upper == upper), g.cost, g.graph_id),
        )
    ]

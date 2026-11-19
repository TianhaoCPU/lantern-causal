"""Binary single-stratum risk difference and conservative observation-gate bounds."""

from collections import defaultdict
from fractions import Fraction

from ..distributions import JointLaw, ObservedLaw, validate_observed


def risk_difference(joint: JointLaw) -> Fraction:
    """Return P(Y=1|X=1)-P(Y=1|X=0), raising on unsupported groups."""
    if any(x not in (0, 1) or y not in (0, 1) or p < 0
           for (x, y), p in joint.items()):
        raise ValueError("Expected a nonnegative binary X,Y mass table.")
    risks = []
    for x in (0, 1):
        denominator = joint.get((x, 0), Fraction()) + joint.get((x, 1), Fraction())
        if denominator == 0:
            raise ValueError(f"No support for the X={x} group.")
        risks.append(joint.get((x, 1), Fraction()) / denominator)
    return risks[1] - risks[0]


def unrestricted_bounds(observed: ObservedLaw) -> tuple[Fraction, Fraction]:
    """Bound the RD by assigning missing X within every Y,Z stratum.

    These are observation-gate bounds, not certified triangle-model bounds.
    If an endpoint creates an empty X group, return the safe natural range.
    """
    validate_observed(observed)
    candidates = []
    for upper in (False, True):
        completed = defaultdict(Fraction)
        for (x, y, r, _), probability in observed.items():
            assigned = x if r else (y if upper else 1 - y)
            completed[assigned, y] += probability
        try:
            candidates.append(risk_difference(completed))
        except ValueError:
            return Fraction(-1), Fraction(1)
    return candidates[0], candidates[1]

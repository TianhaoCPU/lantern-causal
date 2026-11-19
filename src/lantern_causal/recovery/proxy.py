"""Exact inversion for an independently calibrated binary proxy.

Recovery assumes known P(Z|U), proxy error independent of X,Y,R given U,
R independent of X given U,Y, and visible support in each required U,Y cell.
"""

from collections import defaultdict
from fractions import Fraction

from ..distributions import ObservedLaw, validate_observed


def recover_with_calibrated_proxy(
    observed: ObservedLaw, error: Fraction
) -> dict[tuple[int, int], Fraction]:
    """Recover joint X,Y masses from a supplied symmetric proxy error matrix."""
    validate_observed(observed)
    if not 0 <= error <= 1 or error == Fraction(1, 2):
        raise ValueError("Proxy error must be in [0,1] and its matrix nonsingular.")
    determinant = 1 - 2 * error
    all_by_uy = defaultdict(Fraction)
    visible_by_uy = defaultdict(Fraction)
    visible_by_xuy = defaultdict(Fraction)
    for x, y, r in {(x, y, r) for x, y, r, _ in observed}:
        p0, p1 = (observed.get((x, y, r, z), Fraction()) for z in (0, 1))
        unscaled = ((1 - error) * p0 - error * p1,
                    (1 - error) * p1 - error * p0)
        for u, numerator in enumerate(unscaled):
            mass = numerator / determinant
            if mass < 0:
                raise ValueError("Proxy calibration is incompatible with these margins.")
            all_by_uy[u, y] += mass
            if r:
                visible_by_uy[u, y] += mass
                visible_by_xuy[x, u, y] += mass
    recovered = defaultdict(Fraction)
    for (u, y), mass in all_by_uy.items():
        if mass == 0:
            continue
        if visible_by_uy[u, y] == 0:
            raise ValueError("No visible X in a required U,Y stratum.")
        for x in (0, 1):
            recovered[x, y] += (
                visible_by_xuy[x, u, y] / visible_by_uy[u, y] * mass
            )
    return dict(recovered)

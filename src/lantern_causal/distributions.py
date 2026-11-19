"""Exact probability-table contracts used by the synthetic reference modules."""

from collections import defaultdict
from fractions import Fraction
from typing import Mapping

ObservedKey = tuple[int | None, int, int, int]  # X*, Y, R, Z
FullKey = tuple[int, int, int, int]  # X, Y, R, Z
JointKey = tuple[int, int]  # X, Y
ObservedLaw = Mapping[ObservedKey, Fraction]
FullLaw = Mapping[FullKey, Fraction]
JointLaw = Mapping[JointKey, Fraction]


def validate_observed(law: ObservedLaw) -> None:
    """Check normalized binary probabilities and the deterministic observation gate."""
    if not law or sum(law.values()) != 1:
        raise ValueError("The observed law must sum to exactly one.")
    for (x, y, r, z), probability in law.items():
        if y not in (0, 1) or r not in (0, 1) or z not in (0, 1):
            raise ValueError("The reference implementation supports binary Y, R, Z.")
        if (r == 0 and x is not None) or (r == 1 and x not in (0, 1)):
            raise ValueError("X* must be missing exactly when R=0.")
        if probability < 0:
            raise ValueError("Probabilities cannot be negative.")


def observe(full: FullLaw) -> dict[ObservedKey, Fraction]:
    """Apply X*=X when R=1 and a missing marker when R=0."""
    result = defaultdict(Fraction)
    for (x, y, r, z), probability in full.items():
        result[x if r else None, y, r, z] += probability
    validate_observed(result)
    return dict(result)


def marginal_xy(full: FullLaw) -> dict[JointKey, Fraction]:
    """Sum a complete joint table over the recording indicator and proxy."""
    result = defaultdict(Fraction)
    for (x, y, _, _), probability in full.items():
        result[x, y] += probability
    return dict(result)


def visible_xy(observed: ObservedLaw) -> dict[JointKey, Fraction]:
    """Return unnormalized visible X,Y mass, without claiming full-law recovery."""
    validate_observed(observed)
    result = defaultdict(Fraction)
    for (x, y, r, _), probability in observed.items():
        if r:
            result[x, y] += probability
    return dict(result)

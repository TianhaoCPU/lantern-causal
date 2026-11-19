"""Known synthetic mechanisms for validating certificates and recovery separately."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from .distributions import FullKey, ObservedKey, observe


@dataclass(frozen=True)
class SyntheticCase:
    """Full scoring distribution and its corresponding masked analysis view."""

    name: str
    full: dict[FullKey, Fraction]
    observed: dict[ObservedKey, Fraction]


def noisy_copy(source: int, value: int, error: Fraction) -> Fraction:
    """Return one binary-channel conditional probability."""
    return 1 - error if source == value else error


def make_case(
    name: str, error: Fraction = Fraction(1, 20),
    exposure_error: Fraction = Fraction(1, 5),
) -> SyntheticCase:
    """Generate proxy-calibration or same-evidence recovery-bridge examples."""
    if name not in ("proxy", "bridge"):
        raise ValueError(f"Unknown synthetic case: {name}")
    if not 0 < error < Fraction(1, 2) or not 0 < exposure_error < Fraction(1, 2):
        raise ValueError("Reference cases require positive flip errors below one half.")
    full = defaultdict(Fraction)
    for u, x, y, r, z in product((0, 1), repeat=5):
        x_error = exposure_error if name == "proxy" else error
        y_parent = u if name == "proxy" else x
        probability = (
            Fraction(1, 2) * noisy_copy(u, x, x_error)
            * noisy_copy(y_parent, y, error) * noisy_copy(u, r, error)
            * noisy_copy(u, z, error)
        )
        full[x, y, r, z] += probability
    return SyntheticCase(name=name, full=dict(full), observed=observe(full))

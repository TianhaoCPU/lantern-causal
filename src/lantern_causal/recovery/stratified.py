"""Exact empirical RD calculations for the three prespecified missingness graphs.

The analysis functions receive only the observed X*, Y and C. Their estimates
depend on the graph assumptions described in the protocol; no graph is learned
or validated from these calculations. Counts and results are kept exact.
"""

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping


class SupportError(ValueError):
    """A required exposure or observed-data stratum has no support."""


@dataclass(frozen=True)
class FullRow:
    """A complete binary exposure/outcome and its fully observed stratum."""

    x: int
    y: int
    c: str

    def __post_init__(self) -> None:
        _validate_row(self.x, self.y, self.c, allow_missing=False)


@dataclass(frozen=True)
class ObservedRow:
    """Analysis view: x=None is the only representation of a masked X."""

    x: int | None
    y: int
    c: str

    def __post_init__(self) -> None:
        _validate_row(self.x, self.y, self.c, allow_missing=True)


def _validate_row(x: int | None, y: int, c: str, *, allow_missing: bool) -> None:
    if not (type(y) is int and y in (0, 1)):
        raise ValueError("Y must be binary (0 or 1).")
    if not ((allow_missing and x is None) or (type(x) is int and x in (0, 1))):
        raise ValueError("X must be binary; the observed view also allows None.")
    if not isinstance(c, str) or not c.strip():
        raise ValueError("C must be a nonempty stratum label.")


def _counts(rows: Iterable[ObservedRow]) -> Counter:
    counts = Counter()
    for row in rows:
        if not isinstance(row, ObservedRow):
            raise ValueError("Expected ObservedRow values containing only X*, Y and C.")
        counts[row.c, row.x, row.y] += 1
    if not counts:
        raise ValueError("At least one observed row is required.")
    return counts


def _strata(counts: Mapping) -> list[str]:
    return sorted({c for c, _, _ in counts})


def _rd(table: Mapping[tuple[int, int], Fraction], c: str) -> Fraction:
    risks = []
    for x in (0, 1):
        denominator = table.get((x, 0), 0) + table.get((x, 1), 0)
        if not denominator:
            raise SupportError(f"No support for X={x} in stratum {c!r}.")
        risks.append(Fraction(table.get((x, 1), 0)) / denominator)
    return risks[1] - risks[0]


def standardized_reference(rows: Iterable[FullRow]) -> Fraction:
    """Calculate the reference RD with the complete cohort's C weights."""
    counts = Counter()
    for row in rows:
        if not isinstance(row, FullRow):
            raise ValueError("Expected FullRow values for the scoring reference.")
        counts[row.c, row.x, row.y] += 1
    if not counts:
        raise ValueError("At least one full row is required.")
    return _standardized_complete_counts(counts)


def _standardized_complete_counts(counts: Mapping) -> Fraction:
    total = sum(counts.values())
    result = Fraction()
    for c in _strata(counts):
        table = {(x, y): counts.get((c, x, y), 0) for x in (0, 1) for y in (0, 1)}
        n_c = sum(table.values())
        result += Fraction(n_c, total) * _rd(table, c)
    return result


def standardized_visible(rows: Iterable[ObservedRow]) -> Fraction:
    """Use visible X cases, standardized by the entire observed cohort's C weights.

    This estimates the target under R independent of Y given X,C (scenario B).
    It is also the specified standardized complete-case baseline in A and C.
    """
    counts = _counts(rows)
    total = sum(counts.values())
    result = Fraction()
    for c in _strata(counts):
        n_c = sum(n for (stratum, _, _), n in counts.items() if stratum == c)
        table = {(x, y): counts.get((c, x, y), 0) for x in (0, 1) for y in (0, 1)}
        result += Fraction(n_c, total) * _rd(table, c)
    return result


def standardized_mar(rows: Iterable[ObservedRow]) -> Fraction:
    """Estimate the target under R independent of X given Y,C (scenario A)."""
    counts = _counts(rows)
    total = sum(counts.values())
    result = Fraction()
    for c in _strata(counts):
        n_c = sum(n for (stratum, _, _), n in counts.items() if stratum == c)
        table = {}
        for y in (0, 1):
            visible_y = sum(counts.get((c, x, y), 0) for x in (0, 1))
            n_y = visible_y + counts.get((c, None, y), 0)
            if n_y and not visible_y:
                raise SupportError(f"No visible X for Y={y} in stratum {c!r}.")
            for x in (0, 1):
                table[x, y] = Fraction(counts.get((c, x, y), 0) * n_y, visible_y) if n_y else Fraction()
        result += Fraction(n_c, total) * _rd(table, c)
    return result


@dataclass(frozen=True)
class EmpiricalBounds:
    """Sharp finite-count bounds and missing-X allocations for both endpoints.

    Each allocation maps (C, Y) to the number of masked observations assigned
    X=1. The remaining masked observations in that (C,Y) cell are assigned X=0.
    """

    lower: Fraction
    upper: Fraction
    lower_allocation: dict[tuple[str, int], int]
    upper_allocation: dict[tuple[str, int], int]


def _complete(counts: Mapping, allocation: Mapping[tuple[str, int], int]) -> Counter:
    """Complete aggregate counts, checking every allocation against missing cells."""
    strata = _strata(counts)
    expected = {(c, y) for c in strata for y in (0, 1)}
    if set(allocation) != expected:
        raise ValueError("An allocation is required for every C,Y cell.")
    completed = Counter({(c, x, y): n for (c, x, y), n in counts.items() if x is not None})
    for c, y in sorted(expected):
        missing = counts.get((c, None, y), 0)
        assigned = allocation[c, y]
        if type(assigned) is not int or not 0 <= assigned <= missing:
            raise ValueError("A missing-X allocation must be an integer within its cell count.")
        completed[c, 1, y] += assigned
        completed[c, 0, y] += missing - assigned
    return completed


def complete_counts(
    rows: Iterable[ObservedRow], allocation: Mapping[tuple[str, int], int]
) -> dict[tuple[str, int, int], int]:
    """Reconstruct aggregate complete counts from an observed view and a witness."""
    return dict(_complete(_counts(rows), allocation))


def empirical_bounds(rows: Iterable[ObservedRow]) -> EmpiricalBounds:
    """Find exact finite-cohort RD bounds under only the observation gate.

    The RD is nondecreasing as masked deaths are assigned X=1 and nonincreasing
    as masked survivors are assigned X=1. If an extreme makes a group empty,
    assign the minimum one missing observation needed to restore support. If no
    such assignment exists, report a support failure instead of an interval.
    These identification bounds are not sampling confidence intervals.
    """
    counts = _counts(rows)
    lower_allocation, upper_allocation = {}, {}
    for c in _strata(counts):
        missing0, missing1 = (counts.get((c, None, y), 0) for y in (0, 1))
        n_high = sum(counts.get((c, 1, y), 0) for y in (0, 1))
        n_low = sum(counts.get((c, 0, y), 0) for y in (0, 1))
        # Lower: all missing survivors to X=1; upper: all deaths to X=1.
        lo0, lo1 = missing0, 0
        hi0, hi1 = 0, missing1
        if n_high + lo0 + lo1 == 0:
            if not missing1:
                raise SupportError(f"No feasible X=1 support in stratum {c!r}.")
            lo1 = 1
        if n_low + missing0 - lo0 + missing1 - lo1 == 0:
            if not lo0:
                raise SupportError(f"No feasible X=0 support in stratum {c!r}.")
            lo0 -= 1
        if n_high + hi0 + hi1 == 0:
            if not missing0:
                raise SupportError(f"No feasible X=1 support in stratum {c!r}.")
            hi0 = 1
        if n_low + missing0 - hi0 + missing1 - hi1 == 0:
            if not hi1:
                raise SupportError(f"No feasible X=0 support in stratum {c!r}.")
            hi1 -= 1
        lower_allocation[c, 0], lower_allocation[c, 1] = lo0, lo1
        upper_allocation[c, 0], upper_allocation[c, 1] = hi0, hi1
    lower = _standardized_complete_counts(_complete(counts, lower_allocation))
    upper = _standardized_complete_counts(_complete(counts, upper_allocation))
    return EmpiricalBounds(lower, upper, lower_allocation, upper_allocation)

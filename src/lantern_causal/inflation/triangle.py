"""The binary cut-inflation necessary constraint for independent-source triangles.

This uses the triangle construction from Wolfe, Spekkens and Fritz,
https://arxiv.org/abs/1609.00672. It is not a generic graph-compatibility solver.
"""

from dataclasses import dataclass
from fractions import Fraction

from ..distributions import ObservedLaw, validate_observed


@dataclass(frozen=True)
class TriangleCertificate:
    """Exact necessary-condition values for the specified R,Z,Y triangle."""

    required_mismatch: Fraction
    path_upper_bound: Fraction

    @property
    def incompatible(self) -> bool:
        """Return true only if the observed law violates the necessary inequality."""
        return self.required_mismatch > self.path_upper_bound

    def as_dict(self) -> dict:
        """Serialize exact and decimal values and explicitly limit the scope."""
        return {
            "constraint": "binary_triangle_cut",
            "required_mismatch": float(self.required_mismatch),
            "required_mismatch_exact": str(self.required_mismatch),
            "path_upper_bound": float(self.path_upper_bound),
            "path_upper_bound_exact": str(self.path_upper_bound),
            "status": "incompatible" if self.incompatible else "not_excluded",
            "scope": "Exact binary R,Z,Y marginal; three independent pair sources and no direct arrows.",
        }


def cut_triangle_certificate(observed: ObservedLaw) -> TriangleCertificate:
    """Compute the triangle constraint from observable margins, never hidden U."""
    validate_observed(observed)
    p_r = sum(p for (_, _, r, _), p in observed.items() if r)
    p_y = sum(p for (_, y, _, _), p in observed.items() if y)
    mismatch_rz = sum(p for (_, _, r, z), p in observed.items() if r != z)
    mismatch_zy = sum(p for (_, y, _, z), p in observed.items() if z != y)
    return TriangleCertificate(
        p_r * (1 - p_y) + (1 - p_r) * p_y,
        mismatch_rz + mismatch_zy,
    )

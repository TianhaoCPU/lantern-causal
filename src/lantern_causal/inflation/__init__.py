"""Verified special-case inflation constraints; no generic LP backend yet."""

from .triangle import TriangleCertificate, cut_triangle_certificate

__all__ = ["TriangleCertificate", "cut_triangle_certificate"]

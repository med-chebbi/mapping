"""Reverse status calculation from projection completeness."""

from __future__ import annotations

from .model import ConceptProjection, ReferenceEvidence, ReverseStatus


def calculate_reverse_status(
    projections: tuple[ConceptProjection, ...], references: tuple[ReferenceEvidence, ...]
) -> tuple[ReverseStatus, tuple[str, ...], str]:
    if not projections:
        return ReverseStatus.UNSUPPORTED, (), "No supported FLYNC concept corresponds to this AUTOSAR structure."
    if len(projections) > 1:
        concepts = tuple(item.concept for item in projections)
        return ReverseStatus.AMBIGUOUS, concepts, "Multiple FLYNC concept projections remain credible."
    projection = projections[0]
    unresolved = tuple(item for item in references if item.state != "resolved")
    if projection.missing_properties or unresolved:
        reasons = []
        if projection.missing_properties:
            reasons.append("required FLYNC properties cannot be recovered")
        if unresolved:
            reasons.append("one or more ARXML references are missing or ambiguous")
        return ReverseStatus.PARTIAL, (), "; ".join(reasons).capitalize() + "."
    return ReverseStatus.PROJECTED, (), "The AUTOSAR structure contains the required evidence for this FLYNC concept projection."

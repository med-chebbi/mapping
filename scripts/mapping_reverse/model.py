"""Typed reverse-mapping result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping

from mapping_v3.model import SourceLocation


class ReverseStatus(StrEnum):
    PROJECTED = "Projected"
    PARTIAL = "Partial"
    AMBIGUOUS = "Ambiguous"
    UNSUPPORTED = "Unsupported"


@dataclass(frozen=True)
class ReferenceEvidence:
    kind: str
    reference: str
    destination: str | None
    state: str
    targets: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ConceptProjection:
    concept: str
    group: str
    domain: str
    recoverable_properties: Mapping[str, Any]
    missing_properties: tuple[str, ...]
    known_transformations: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ReverseRow:
    key: str
    source: SourceLocation
    arxml_tag: str
    short_name: str | None
    hierarchy: tuple[str, ...]
    semantic_properties: Mapping[str, Any]
    projections: tuple[ConceptProjection, ...]
    references: tuple[ReferenceEvidence, ...]
    status: ReverseStatus
    ambiguity: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "arxml_source": asdict(self.source),
            "arxml_element": {"tag": self.arxml_tag, "short_name": self.short_name, "hierarchy": list(self.hierarchy)},
            "projected_flync_concepts": [item.concept for item in self.projections],
            "semantic_properties": dict(sorted(self.semantic_properties.items())),
            "recoverable_flync_properties": {item.concept: dict(sorted(item.recoverable_properties.items())) for item in self.projections},
            "missing_flync_properties": {item.concept: list(item.missing_properties) for item in self.projections},
            "projection_evidence": {item.concept: list(item.evidence) for item in self.projections},
            "known_transformations": {item.concept: list(item.known_transformations) for item in self.projections},
            "resolved_references": [asdict(item) for item in self.references],
            "status": self.status.value,
            "ambiguity": list(self.ambiguity),
            "rationale": self.rationale,
        }

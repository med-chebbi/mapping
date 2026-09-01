"""Reverse projection orchestration."""

from __future__ import annotations

from pathlib import Path

from mapping_v3.arxml import ArxmlIndex

from .completeness import calculate_reverse_status
from .model import ReverseRow
from .projectors import project_element, resolve_references


class ReverseMappingEngine:
    def __init__(self, arxml_root: Path):
        self.index = ArxmlIndex(arxml_root)

    def map(self, domain: str = "all", concept: str = "all") -> tuple[ReverseRow, ...]:
        rows = []
        for element in self.index.elements:
            if element.short_name is None:
                continue
            projections = project_element(element, self.index, domain, concept)
            if (domain != "all" or concept != "all") and not projections:
                continue
            references = resolve_references(element, self.index)
            status, ambiguity, rationale = calculate_reverse_status(projections, references)
            semantic_properties = {key.lower(): values[0] if len(values) == 1 else values for key, values in sorted(element.properties.items())}
            rows.append(
                ReverseRow(
                    key=element.key,
                    source=element.source,
                    arxml_tag=element.tag,
                    short_name=element.short_name,
                    hierarchy=element.hierarchy,
                    semantic_properties=semantic_properties,
                    projections=projections,
                    references=references,
                    status=status,
                    ambiguity=ambiguity,
                    rationale=rationale,
                )
            )
        return tuple(sorted(rows, key=lambda item: item.key))


def run_reverse_mapping(arxml_root: Path, domain: str = "all", concept: str = "all") -> tuple[ReverseRow, ...]:
    return ReverseMappingEngine(arxml_root).map(domain, concept)

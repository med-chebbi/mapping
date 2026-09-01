"""Mapping orchestration over independent discovery and rule layers."""

from __future__ import annotations

from pathlib import Path

from .arxml import ArxmlIndex
from .flync import FlyncModel
from .model import Domain, MappingRow
from .rules import resolve_element
from .status import calculate_status


class MappingEngine:
    def __init__(self, flync_root: Path, arxml_root: Path):
        self.flync = FlyncModel(flync_root)
        self.arxml = ArxmlIndex(arxml_root)

    def map(self, domain: str) -> tuple[MappingRow, ...]:
        requested = Domain(domain) if domain != "all" else None
        rows: list[MappingRow] = []
        for element in self.flync.elements:
            domains = element.domains
            if requested and requested not in domains and Domain.SHARED not in domains:
                continue
            row_domain = requested if requested and Domain.SHARED in domains else sorted(domains, key=lambda item: item.value)[0]
            candidates, evidence = resolve_element(element, self.arxml)
            status, rationale = calculate_status(len(candidates), evidence)
            rows.append(
                MappingRow(
                    domain=row_domain,
                    category=element.category,
                    flync_key=element.key,
                    flync_source=element.source,
                    flync_element=element.name,
                    flync_external_key=element.external_key,
                    flync_context=element.context,
                    arxml_elements=candidates,
                    evidence=evidence,
                    status=status,
                    rationale=rationale,
                )
            )
        return tuple(sorted(rows, key=lambda row: (row.domain.value, row.category, row.flync_key)))


def run_mapping(domain: str, flync_root: Path, arxml_root: Path) -> tuple[MappingRow, ...]:
    if domain not in {"classic", "adaptive", "all"}:
        raise ValueError(f"Unsupported domain: {domain}")
    return MappingEngine(flync_root, arxml_root).map(domain)

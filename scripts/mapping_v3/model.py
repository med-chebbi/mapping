"""Typed normalized models shared by the V3 mapper layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class Domain(StrEnum):
    CLASSIC = "classic"
    ADAPTIVE = "adaptive"
    SHARED = "shared"


class MatchResult(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    TRANSFORMED = "transformed"
    SUPPORTING = "supporting"


class Status(StrEnum):
    MAPPED = "Mapped"
    PARTIAL = "Partial"
    NOT_MAPPED = "Not mapped"


@dataclass(frozen=True, order=True)
class SourceLocation:
    file: str
    path: str


@dataclass(frozen=True)
class DatatypeNode:
    kind: str
    name: str | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)
    children: tuple[tuple[str, "DatatypeNode"], ...] = ()

    def flatten(self, prefix: str = "root") -> tuple[tuple[str, str, Any], ...]:
        values: list[tuple[str, str, Any]] = [(prefix, "kind", self.kind)]
        if self.name is not None:
            values.append((prefix, "name", self.name))
        for key, value in sorted(self.properties.items()):
            values.append((prefix, key, value))
        for label, child in self.children:
            values.extend(child.flatten(f"{prefix}.{label}"))
        return tuple(values)


@dataclass(frozen=True)
class FlyncReference:
    kind: str
    value: Any
    target_category: str | None = None


@dataclass(frozen=True)
class FlyncElement:
    key: str
    category: str
    domains: frozenset[Domain]
    name: str
    source: SourceLocation
    external_key: str | None = None
    parent: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)
    properties: Mapping[str, Any] = field(default_factory=dict)
    references: tuple[FlyncReference, ...] = ()
    datatype: DatatypeNode | None = None


@dataclass(frozen=True)
class ArxmlReference:
    kind: str
    value: str
    dest: str | None
    owner_key: str


@dataclass(frozen=True)
class ArxmlElement:
    key: str
    tag: str
    short_name: str | None
    source: SourceLocation
    package_path: tuple[str, ...]
    hierarchy: tuple[str, ...]
    properties: Mapping[str, tuple[str, ...]]
    attributes: Mapping[str, str]
    references: tuple[ArxmlReference, ...]
    parent_key: str | None

    @property
    def autosar_path(self) -> str | None:
        if not self.short_name:
            return None
        return "/" + "/".join((*self.hierarchy, self.short_name))


@dataclass(frozen=True)
class Resolution:
    state: str
    reference: str
    candidates: tuple[str, ...] = ()
    rationale: str = ""


@dataclass(frozen=True)
class Evidence:
    kind: str
    result: MatchResult
    required: bool
    flync_value: Any = None
    arxml_value: Any = None
    arxml_keys: tuple[str, ...] = ()
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["result"] = self.result.value
        return result


@dataclass(frozen=True)
class MappingRow:
    domain: Domain
    category: str
    flync_key: str
    flync_source: SourceLocation
    flync_element: str
    flync_external_key: str | None
    flync_context: Mapping[str, Any]
    arxml_elements: tuple[ArxmlElement, ...]
    evidence: tuple[Evidence, ...]
    status: Status
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "category": self.category,
            "flync_key": self.flync_key,
            "flync_source": asdict(self.flync_source),
            "flync_element": self.flync_element,
            "flync_external_key": self.flync_external_key,
            "flync_context": dict(sorted(self.flync_context.items())),
            "arxml_elements": [
                {
                    "file": element.source.file,
                    "path": element.source.path,
                    "tag": element.tag,
                    "short_name": element.short_name,
                    "package_path": list(element.package_path),
                }
                for element in self.arxml_elements
            ],
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status.value,
            "rationale": self.rationale,
        }

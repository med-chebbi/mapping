"""Recursive FLYNC and AUTOSAR datatype normalization and comparison."""

from __future__ import annotations

from typing import Any

from .arxml import ArxmlIndex
from .model import ArxmlElement, DatatypeNode, Evidence, MatchResult

PRIMITIVES = {"boolean", "uint8", "uint16", "uint32", "uint64", "int8", "int16", "int32", "int64", "float32", "float64"}


def normalize_flync_datatype(value: Any) -> DatatypeNode | None:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        return None
    kind = value["type"]
    name = value.get("name")
    ignored = {"type", "name", "description", "members", "element_type", "datatyperef", "base_type", "entries", "fields"}
    properties = {key: item for key, item in value.items() if key not in ignored}
    children: list[tuple[str, DatatypeNode]] = []
    if kind == "enum":
        base = normalize_flync_datatype(value.get("base_type") or {"type": "uint8"})
        if base:
            children.append(("base_type", base))
        properties["entries"] = tuple((entry.get("value"), entry.get("name")) for entry in value.get("entries", []))
    elif kind == "struct":
        for index, member in enumerate(value.get("members", [])):
            child = normalize_flync_datatype(member)
            if child:
                label = member.get("member_name") or member.get("name") or str(index)
                children.append((f"member[{label}]", child))
    elif kind == "array":
        properties["dimensions"] = tuple(tuple(sorted(dimension.items())) for dimension in value.get("dimensions", []))
        child = normalize_flync_datatype(value.get("element_type"))
        if child:
            children.append(("element_type", child))
    elif kind == "typedef":
        child = normalize_flync_datatype(value.get("datatyperef"))
        if child:
            children.append(("target", child))
    elif kind == "union":
        for index, member in enumerate(value.get("members", [])):
            raw = member.get("type")
            raw_type = raw if isinstance(raw, dict) else {"type": raw}
            child = normalize_flync_datatype(raw_type)
            if child:
                children.append((f"member[{member.get('index', index)}:{member.get('name', index)}]", child))
    elif kind == "bitfield":
        properties["fields"] = tuple(
            (entry.get("name"), entry.get("bitposition"), tuple((item.get("value"), item.get("name")) for item in entry.get("values", [])))
            for entry in value.get("fields") or []
        )
    return DatatypeNode(kind, name, properties, tuple(children))


def normalize_arxml_datatype(element: ArxmlElement, index: ArxmlIndex, visited: frozenset[str] = frozenset()) -> DatatypeNode:
    if element.key in visited:
        return DatatypeNode("cycle", element.short_name)
    visited = visited | {element.key}
    tag = element.tag
    kind = "unknown"
    if "PRIMITIVE" in tag:
        kind = _primitive_from_name(element.short_name)
    elif "RECORD" in tag or "STRUCTURE" in element.properties.get("CATEGORY", ()):
        kind = "struct"
    elif "ARRAY" in tag or "ARRAY" in element.properties.get("CATEGORY", ()):
        kind = "array"
    elif "TYPEDEF" in tag:
        kind = "typedef"
    elif "UNION" in tag:
        kind = "union"
    elif "STRING" in tag:
        kind = "string"
    elif "IMPLEMENTATION-DATA-TYPE" == tag:
        kind = _primitive_from_name(element.short_name)
    children: list[tuple[str, DatatypeNode]] = []
    for reference in element.references:
        if "TYPE" not in reference.kind:
            continue
        resolution = index.resolve(reference.value, element, reference.dest)
        if resolution.state == "resolved":
            target = index.by_key[resolution.candidates[0]]
            children.append((reference.kind.lower(), normalize_arxml_datatype(target, index, visited)))
        else:
            children.append((reference.kind.lower(), DatatypeNode(resolution.state, reference.value)))
    properties = {
        key.lower(): values[0] if len(values) == 1 else values
        for key, values in element.properties.items()
        if key in {"CATEGORY", "ARRAY-SIZE", "SW-DATA-DEF-PROPS"}
    }
    return DatatypeNode(kind, element.short_name, properties, tuple(children))


def _primitive_from_name(name: str | None) -> str:
    normalized = (name or "").lower().replace("_", "")
    for primitive in sorted(PRIMITIVES, key=len, reverse=True):
        if primitive in normalized:
            return primitive
    return "primitive"


def compare_datatypes(flync: DatatypeNode, arxml: DatatypeNode | None, arxml_key: str | None = None) -> tuple[Evidence, ...]:
    if arxml is None:
        return (Evidence("datatype", MatchResult.MISSING, True, flync.kind, None, (), "no resolved ARXML datatype definition"),)
    evidence: list[Evidence] = []

    def walk(left: DatatypeNode, right: DatatypeNode | None, path: str) -> None:
        keys = (arxml_key,) if arxml_key else ()
        if right is None:
            evidence.append(Evidence(f"datatype:{path}", MatchResult.MISSING, True, left.kind, None, keys, "ARXML datatype child is absent"))
            return
        if right.kind in {"missing", "ambiguous", "unresolved"}:
            result = MatchResult.AMBIGUOUS if right.kind == "ambiguous" else MatchResult.UNRESOLVED
            evidence.append(Evidence(f"datatype:{path}", result, True, left.kind, right.name, keys, "datatype reference did not resolve uniquely"))
            return
        matches = left.kind == right.kind or (left.kind in PRIMITIVES and right.kind == "primitive")
        evidence.append(
            Evidence(
                f"datatype:{path}:kind",
                MatchResult.MATCH if matches else MatchResult.MISMATCH,
                True,
                left.kind,
                right.kind,
                keys,
                "recursive datatype-kind comparison",
            )
        )
        for index_value, (label, child) in enumerate(left.children):
            counterpart = right.children[index_value][1] if index_value < len(right.children) else None
            walk(child, counterpart, f"{path}.{label}")

    walk(flync, arxml, "root")
    return tuple(evidence)

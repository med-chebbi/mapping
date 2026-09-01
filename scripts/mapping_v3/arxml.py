"""Recursive ARXML discovery, normalization, indexing, and reference resolution."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from .model import ArxmlElement, ArxmlReference, Resolution, SourceLocation


class ArxmlError(RuntimeError):
    """Raised for invalid or missing ARXML input."""


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _short_name(node: ET.Element) -> str | None:
    for child in node:
        if local_name(child.tag) == "SHORT-NAME":
            return (child.text or "").strip() or None
    return None


class ArxmlIndex:
    """Deterministic index over every ARXML document below an input root."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ArxmlError(f"ARXML root is not a directory: {root}")
        self.files = tuple(sorted(self.root.rglob("*.arxml"), key=lambda value: value.as_posix().lower()))
        if not self.files:
            raise ArxmlError(f"No .arxml files found below: {root}")
        self.namespaces: set[str] = set()
        elements: list[ArxmlElement] = []
        for path in self.files:
            elements.extend(self._parse(path))
        self.elements = tuple(sorted(elements, key=lambda value: value.key))
        self.by_key = {element.key: element for element in self.elements}
        self.by_tag: dict[str, tuple[ArxmlElement, ...]] = {}
        self.by_name: dict[str, tuple[ArxmlElement, ...]] = {}
        self.by_path: dict[str, tuple[ArxmlElement, ...]] = {}
        for attribute, selector in (
            ("by_tag", lambda item: item.tag),
            ("by_name", lambda item: item.short_name),
            ("by_path", lambda item: item.autosar_path),
        ):
            grouped: dict[str, list[ArxmlElement]] = defaultdict(list)
            for element in self.elements:
                key = selector(element)
                if key:
                    grouped[key].append(element)
            setattr(self, attribute, {key: tuple(sorted(value, key=lambda item: item.key)) for key, value in grouped.items()})

    def _parse(self, path: Path) -> list[ArxmlElement]:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise ArxmlError(f"Invalid XML in {path}: {exc}") from exc
        if root.tag.startswith("{"):
            self.namespaces.add(root.tag[1:].split("}", 1)[0])
        relative = path.relative_to(self.root).as_posix()
        parent_map = {child: parent for parent in root.iter() for child in parent}
        sibling_indexes: dict[ET.Element, int] = {}
        for parent in root.iter():
            counts: dict[str, int] = defaultdict(int)
            for child in parent:
                tag = local_name(child.tag)
                counts[tag] += 1
                sibling_indexes[child] = counts[tag]

        def package_path(node: ET.Element) -> tuple[str, ...]:
            names: list[str] = []
            current: ET.Element | None = node
            while current is not None:
                if local_name(current.tag) == "AR-PACKAGE":
                    name = _short_name(current)
                    if name:
                        names.append(name)
                current = parent_map.get(current)
            return tuple(reversed(names))

        def structural_path(node: ET.Element) -> str:
            parts: list[str] = []
            current: ET.Element | None = node
            while current is not None:
                tag = local_name(current.tag)
                name = _short_name(current)
                qualifier = f"[SHORT-NAME='{name}']" if name else f"[{sibling_indexes.get(current, 1)}]"
                parts.append(tag + qualifier)
                current = parent_map.get(current)
            return "/" + "/".join(reversed(parts))

        output: list[ArxmlElement] = []
        keys: dict[ET.Element, str] = {}
        for node in root.iter():
            keys[node] = f"{relative}:{structural_path(node)}"

        def owned_descendants(node: ET.Element):
            for child in node:
                if _short_name(child) is not None:
                    continue
                yield child
                yield from owned_descendants(child)

        for node in root.iter():
            properties: dict[str, list[str]] = defaultdict(list)
            references: list[ArxmlReference] = []
            for descendant in owned_descendants(node):
                tag = local_name(descendant.tag)
                text = (descendant.text or "").strip()
                if text and len(descendant) == 0:
                    properties[tag].append(text)
                if (tag.endswith("-REF") or tag.endswith("-TREF")) and text:
                    references.append(ArxmlReference(tag, text, descendant.attrib.get("DEST"), keys[node]))
            hierarchy: list[str] = []
            current = parent_map.get(node)
            while current is not None:
                name = _short_name(current)
                if name:
                    hierarchy.append(name)
                current = parent_map.get(current)
            output.append(
                ArxmlElement(
                    key=keys[node],
                    tag=local_name(node.tag),
                    short_name=_short_name(node),
                    source=SourceLocation(relative, structural_path(node)),
                    package_path=package_path(node),
                    hierarchy=tuple(reversed(hierarchy)),
                    properties={key: tuple(values) for key, values in sorted(properties.items())},
                    attributes=dict(sorted(node.attrib.items())),
                    references=tuple(sorted(references, key=lambda item: (item.kind, item.value, item.dest or ""))),
                    parent_key=keys.get(parent_map.get(node)),
                )
            )
        return output

    def candidates(self, tags: tuple[str, ...], name: str | None = None) -> tuple[ArxmlElement, ...]:
        values = [element for tag in tags for element in self.by_tag.get(tag, ())]
        if name is not None:
            values = [element for element in values if element.short_name == name]
        unique = {element.key: element for element in values}
        return tuple(sorted(unique.values(), key=lambda element: element.key))

    def resolve(self, reference: str, owner: ArxmlElement | None = None, dest: str | None = None) -> Resolution:
        normalized = "/" + reference.strip().strip("/")
        exact = list(self.by_path.get(normalized, ()))
        if dest:
            exact = [item for item in exact if item.tag == dest]
        if len(exact) == 1:
            return Resolution("resolved", reference, (exact[0].key,), "unique canonical AUTOSAR path")
        if len(exact) > 1:
            return Resolution("ambiguous", reference, tuple(item.key for item in exact), "duplicate canonical AUTOSAR path")
        terminal = normalized.rsplit("/", 1)[-1]
        candidates = list(self.by_name.get(terminal, ()))
        if dest:
            candidates = [item for item in candidates if item.tag == dest]
        if owner and not reference.startswith("/"):
            owner_package = owner.package_path
            contextual = [item for item in candidates if item.package_path[: len(owner_package)] == owner_package]
            if contextual:
                candidates = contextual
        if len(candidates) == 1:
            return Resolution("resolved", reference, (candidates[0].key,), "unique context-filtered terminal reference")
        if len(candidates) > 1:
            return Resolution("ambiguous", reference, tuple(item.key for item in candidates), "multiple context-compatible targets")
        return Resolution("missing", reference, (), "no compatible ARXML target")

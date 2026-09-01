"""Semantic ARXML-to-FLYNC concept projection rules."""

from __future__ import annotations

from typing import Any

from mapping_v3.arxml import ArxmlIndex
from mapping_v3.model import ArxmlElement

from .concepts import BY_TAG, ConceptSpec
from .datatypes import datatype_properties
from .model import ConceptProjection, ReferenceEvidence
from .ownership import ownership_properties


def _leaf_value(element: ArxmlElement, leaves: tuple[str, ...]) -> Any:
    values = tuple(value for leaf in leaves for value in element.properties.get(leaf, ()))
    if not values:
        return None
    return values[0] if len(values) == 1 else values


def resolve_references(element: ArxmlElement, index: ArxmlIndex) -> tuple[ReferenceEvidence, ...]:
    output = []
    for reference in element.references:
        resolution = index.resolve(reference.value, element, reference.dest)
        output.append(
            ReferenceEvidence(
                reference.kind,
                reference.value,
                reference.dest,
                resolution.state,
                resolution.candidates,
                resolution.rationale,
            )
        )
    return tuple(sorted(output, key=lambda item: (item.kind, item.reference, item.destination or "")))


def _project(element: ArxmlElement, spec: ConceptSpec, index: ArxmlIndex) -> ConceptProjection:
    recovered: dict[str, Any] = {}
    evidence = [f"AUTOSAR type {element.tag} is compatible with FLYNC concept {spec.name}"]
    if element.short_name:
        recovered["name"] = element.short_name
        evidence.append("SHORT-NAME provides semantic identity")
    for name, leaves in spec.properties:
        value = _leaf_value(element, leaves)
        if value is not None:
            recovered[name] = value
            evidence.append(f"{name} recovered from {', '.join(leaves)}")
    recovered.update(ownership_properties(element))
    if spec.name == "datatype":
        recovered.update(datatype_properties(element, index))
    if spec.name == "datatype_parameter":
        type_references = tuple(item.value for item in element.references if "TYPE" in item.kind)
        if type_references:
            recovered["datatype_reference"] = type_references[0] if len(type_references) == 1 else type_references
    missing = set(name for name in spec.required if recovered.get(name) is None)
    if spec.name == "someip_field":
        for accessor in ("getter", "setter", "notifier"):
            if str(recovered.get(f"has_{accessor}", "false")).lower() == "true" and recovered.get(f"{accessor}_id") is None:
                missing.add(f"{accessor}_id")
    missing.update(spec.normally_unrecoverable)
    return ConceptProjection(spec.name, spec.group, spec.domain, recovered, tuple(sorted(missing)), spec.transformations, tuple(evidence))


def project_element(element: ArxmlElement, index: ArxmlIndex, domain: str = "all", concept: str = "all") -> tuple[ConceptProjection, ...]:
    specs = BY_TAG.get(element.tag, ())
    ancestor_tags = set()
    parent_key = element.parent_key
    while parent_key:
        parent = index.by_key[parent_key]
        ancestor_tags.add(parent.tag)
        parent_key = parent.parent_key
    specs = tuple(spec for spec in specs if not spec.ancestor_tags or ancestor_tags.intersection(spec.ancestor_tags))
    if domain != "all":
        specs = tuple(spec for spec in specs if spec.domain in {domain, "shared"})
    if concept != "all":
        specs = tuple(spec for spec in specs if spec.group == concept or spec.name == concept)
    return tuple(_project(element, spec, index) for spec in specs)

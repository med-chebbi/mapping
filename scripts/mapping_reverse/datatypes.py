"""Reverse datatype evidence derived from the V3 ARXML datatype index."""

from __future__ import annotations

from mapping_v3.arxml import ArxmlIndex
from mapping_v3.datatypes import normalize_arxml_datatype
from mapping_v3.model import ArxmlElement


def datatype_properties(element: ArxmlElement, index: ArxmlIndex) -> dict:
    node = normalize_arxml_datatype(element, index)
    return {"datatype_tree": node.flatten()}

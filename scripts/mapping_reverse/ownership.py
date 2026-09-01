"""Ownership evidence recovered from normalized ARXML containment."""

from __future__ import annotations

from mapping_v3.model import ArxmlElement


def ownership_properties(element: ArxmlElement) -> dict[str, object]:
    if not element.hierarchy:
        return {}
    return {"owner_hierarchy": element.hierarchy, "immediate_owner": element.hierarchy[-1]}

"""Deterministic reverse-mapping JSON and CSV output."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .model import ReverseRow

OUTPUT_FIELDS = (
    "key",
    "arxml_source",
    "arxml_element",
    "projected_flync_concepts",
    "semantic_properties",
    "recoverable_flync_properties",
    "missing_flync_properties",
    "projection_evidence",
    "known_transformations",
    "resolved_references",
    "status",
    "ambiguity",
    "rationale",
)


def write_reverse_output(rows: Iterable[ReverseRow], output: Path) -> None:
    document_rows = [row.to_dict() for row in rows]
    output = output.resolve()
    if output.suffix.lower() not in {".json", ".csv"}:
        raise ValueError("--output must end in .json or .csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        output.write_text(
            json.dumps(
                {"schema_version": 1, "direction": "arxml-to-flync-concepts", "rows": document_rows}, indent=2, ensure_ascii=False, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        return
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in document_rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value
                    for key, value in row.items()
                }
            )

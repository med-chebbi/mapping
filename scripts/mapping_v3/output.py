"""Deterministic JSON and CSV output generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .model import MappingRow


def write_output(rows: Iterable[MappingRow], output: Path) -> None:
    ordered = tuple(rows)
    output = output.resolve()
    if output.suffix.lower() not in {".json", ".csv"}:
        raise ValueError("--output must end in .json or .csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        document = {"schema_version": 3, "rows": [row.to_dict() for row in ordered]}
        output.write_text(json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        return
    fields = [
        "domain",
        "category",
        "flync_key",
        "flync_source",
        "flync_element",
        "flync_external_key",
        "flync_context",
        "arxml_elements",
        "evidence",
        "status",
        "rationale",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ordered:
            value = row.to_dict()
            for key in ("flync_source", "flync_context", "arxml_elements", "evidence"):
                value[key] = json.dumps(value[key], ensure_ascii=False, sort_keys=True)
            writer.writerow(value)

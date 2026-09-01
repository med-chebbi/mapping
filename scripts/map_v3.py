#!/usr/bin/env python3
"""Generic, evidence-based FLYNC-to-AUTOSAR traceability CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mapping_v3.arxml import ArxmlError
from mapping_v3.engine import run_mapping
from mapping_v3.flync import FlyncError
from mapping_v3.output import write_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map a FLYNC workspace to recursively discovered AUTOSAR ARXML evidence.")
    parser.add_argument(
        "--domain", required=True, choices=("classic", "adaptive", "all"), help="Filter normalized elements by communication domain."
    )
    parser.add_argument("--flync", required=True, type=Path, help="FLYNC workspace root.")
    parser.add_argument("--arxml", required=True, type=Path, help="Root below which all ARXML documents are discovered.")
    parser.add_argument("--output", required=True, type=Path, help="Deterministic .json or .csv output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = run_mapping(args.domain, args.flync, args.arxml)
        write_output(rows, args.output)
    except (ArxmlError, FlyncError, OSError, ValueError) as exc:
        print(f"mapping failed: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {len(rows)} mapping rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

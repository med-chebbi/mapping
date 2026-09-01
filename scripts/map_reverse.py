#!/usr/bin/env python3
"""ARXML-to-FLYNC concept and evidence projection CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mapping_reverse.engine import run_reverse_mapping
from mapping_reverse.output import write_reverse_output
from mapping_v3.arxml import ArxmlError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project AUTOSAR ARXML structures onto supported FLYNC concepts and evidence.")
    parser.add_argument("--arxml", required=True, type=Path, help="Root below which ARXML documents are discovered.")
    parser.add_argument("--output", required=True, type=Path, help="Deterministic .json or .csv output path.")
    parser.add_argument("--domain", choices=("classic", "adaptive", "all"), default="all", help="Filter projected concepts by domain.")
    parser.add_argument(
        "--concept",
        choices=("all", "ecu", "controller", "can", "ethernet", "someip", "datatype", "topology"),
        default="all",
        help="Filter projected FLYNC concepts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = run_reverse_mapping(args.arxml, args.domain, args.concept)
        write_reverse_output(rows, args.output)
    except (ArxmlError, OSError, ValueError) as exc:
        print(f"reverse mapping failed: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {len(rows)} reverse mapping rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface for configuration-driven pipeline analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import run_config_file, write_records_csv


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return ""
    return str(value)


def print_summary(records: list[dict[str, float | str | bool | int | None]]) -> None:
    """Print a compact analysis summary to stdout."""

    columns = ["feature_id", "method", "failure_pressure", "safe_pressure", "passes_maop"]
    widths = {
        column: max(len(column), *(len(_format_value(record.get(column))) for record in records))
        for column in columns
    }
    print("  ".join(column.ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for record in records:
        print("  ".join(_format_value(record.get(column)).ljust(widths[column]) for column in columns))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run B31G, DNV RP-F101, and optional RSTRENG analysis from one input file.",
    )
    parser.add_argument(
        "--input",
        default="pipeline_input.json",
        help="JSON input file containing pipeline parameters and corrosion features.",
    )
    parser.add_argument(
        "--output",
        default="analysis_results.csv",
        help="CSV output file for analysis results.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    records = run_config_file(args.input)
    write_records_csv(records, args.output)
    print_summary(records)
    print(f"\nWrote {len(records)} result rows to {Path(args.output)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

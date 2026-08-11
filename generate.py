#!/usr/bin/env python3
"""Generate IRPF HTML guide from an IBKR Activity Statement CSV."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.calculator import compute_irpf, resolve_prior_year, save_year_json
from src.parser import parse_statement
from src.ptax import make_ptax_lookup
from src.report import write_report


def _collect_ptax_dates(statement, year: int) -> set[date]:
    dates: set[date] = set()
    if statement.meta.period_end:
        dates.add(statement.meta.period_end)
    else:
        dates.add(date(year, 12, 31))

    for trade in statement.trades:
        if trade.date.year == year:
            dates.add(trade.date)
    for dividend in statement.dividends:
        if dividend.date.year == year:
            dates.add(dividend.date)
    return dates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate IRPF HTML guide from IBKR Activity Statement CSV.",
    )
    parser.add_argument("--year", type=int, required=True, help="Target tax year (e.g. 2025)")
    parser.add_argument("--statement", type=Path, required=True, help="Path to Activity Statement CSV")
    parser.add_argument(
        "--output",
        type=Path,
        help="HTML output path (default: output/irpf-{year}.html)",
    )
    parser.add_argument(
        "--prior-statement",
        type=Path,
        help="Optional prior-year Activity Statement for 31/12 prior values",
    )
    parser.add_argument(
        "--prior-year-json",
        type=Path,
        help="Optional JSON from previous run (default: output/irpf-{year-1}.json)",
    )
    parser.add_argument(
        "--ptax-cache",
        type=Path,
        default=Path("cache/ptax"),
        help="Directory for PTAX cache (default: cache/ptax)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.statement.exists():
        print(f"Statement not found: {args.statement}", file=sys.stderr)
        return 1

    output_path = args.output or Path(f"output/irpf-{args.year}.html")
    json_path = output_path.with_suffix(".json")
    prior_json = args.prior_year_json or Path(f"output/irpf-{args.year - 1}.json")

    statement = parse_statement(args.statement)
    ptax_lookup = make_ptax_lookup(cache_dir=args.ptax_cache)

    # Warm PTAX cache for all needed dates
    for d in _collect_ptax_dates(statement, args.year):
        ptax_lookup(d)

    prior_positions = resolve_prior_year(
        statement=statement,
        year=args.year,
        prior_json_path=prior_json,
        prior_statement_path=args.prior_statement,
        ptax_lookup=ptax_lookup,
    )

    report = compute_irpf(
        statement=statement,
        year=args.year,
        ptax_lookup=ptax_lookup,
        prior_positions_brl=prior_positions,
    )

    write_report(report, output_path)
    save_year_json(report, json_path)

    print(f"HTML: {output_path}")
    print(f"JSON: {json_path}")
    if report.validation_notes:
        print("Validation notes:")
        for note in report.validation_notes:
            print(f"  - {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

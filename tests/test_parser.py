from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.calculator import compute_irpf
from src.parser import filter_by_year, parse_statement
from src.ptax import make_ptax_lookup

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"
PTAX_RATE = Decimal("5.50")


@pytest.fixture
def ptax_lookup():
    fixed = {
        date(2025, 3, 10): PTAX_RATE,
        date(2025, 3, 20): PTAX_RATE,
        date(2025, 6, 15): PTAX_RATE,
        date(2025, 12, 31): PTAX_RATE,
    }
    return make_ptax_lookup(overrides=fixed)


def test_parse_statement_sections():
    statement = parse_statement(FIXTURE)
    assert statement.meta.period_end == date(2025, 12, 31)
    assert len(statement.positions) == 1
    assert statement.positions[0].symbol == "AAPL"
    assert statement.positions[0].value == Decimal("1500")
    assert statement.nav.prior_total == Decimal("0")
    assert len(statement.trades) == 2
    assert len(statement.dividends) == 1


def test_filter_by_year():
    statement = parse_statement(FIXTURE)
    filtered = filter_by_year(statement, 2025)
    assert len(filtered.trades) == 2
    filtered_2024 = filter_by_year(statement, 2024)
    assert len(filtered_2024.trades) == 0


def test_compute_irpf_bens_direitos(ptax_lookup):
    statement = parse_statement(FIXTURE)
    report = compute_irpf(statement, 2025, ptax_lookup, prior_positions_brl={})
    assert len(report.bens_direitos) == 1
    assert report.bens_direitos[0].value_brl == Decimal("8250.00")
    assert report.is_first_ibkr_year is True
    assert report.total_dividends_brl == Decimal("13.75")


def test_monthly_darf_check(ptax_lookup):
    statement = parse_statement(FIXTURE)
    report = compute_irpf(statement, 2025, ptax_lookup, prior_positions_brl={})
    assert len(report.monthly_sales) == 1
    assert report.monthly_sales[0].year_month == "2025-06"
    assert report.monthly_sales[0].needs_darf is False


def test_cbe_below_threshold(ptax_lookup):
    statement = parse_statement(FIXTURE)
    report = compute_irpf(statement, 2025, ptax_lookup, prior_positions_brl={})
    assert report.cbe is not None
    assert report.cbe.cbe_required is False

"""Market values from the Activity Statement (no external price APIs)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from .models import CashBalance, Position, StatementData


def statement_end_date(statement: StatementData, year: int) -> date:
    if statement.meta.period_end:
        return statement.meta.period_end
    return date(year, 12, 31)


def position_value_brl(
    position: Position,
    valuation_date: date,
    ptax_lookup: Callable[[date], Decimal],
) -> Decimal:
    rate = ptax_lookup(valuation_date)
    return (position.value * rate).quantize(Decimal("0.01"))


def cash_value_brl(
    balance: CashBalance,
    valuation_date: date,
    ptax_lookup: Callable[[date], Decimal],
) -> Decimal:
    rate = ptax_lookup(valuation_date)
    return (balance.ending_cash * rate).quantize(Decimal("0.01"))


def total_portfolio_usd(statement: StatementData) -> Decimal:
    positions = sum((p.value for p in statement.positions), Decimal("0"))
    cash = sum((b.ending_cash for b in statement.cash_balances), Decimal("0"))
    accruals = statement.nav.dividend_accruals
    return positions + cash + accruals

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class StatementMeta:
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    base_currency: str = "USD"
    account_id: Optional[str] = None


@dataclass
class Position:
    symbol: str
    quantity: Decimal
    close_price: Decimal
    value: Decimal
    currency: str
    asset_category: str
    cost_basis: Decimal = Decimal("0")
    country: str = ""
    isin: str = ""


@dataclass
class CashBalance:
    currency: str
    ending_cash: Decimal
    description: str = ""


@dataclass
class Trade:
    symbol: str
    date: date
    quantity: Decimal
    price: Decimal
    proceeds: Decimal
    commission: Decimal
    basis: Decimal
    realized_pl: Decimal
    currency: str
    asset_category: str
    code: str = ""


@dataclass
class Dividend:
    symbol: str
    date: date
    amount: Decimal
    currency: str
    description: str = ""


@dataclass
class WithholdingTax:
    symbol: str
    date: date
    amount: Decimal
    currency: str
    description: str = ""


@dataclass
class DepositWithdrawal:
    date: date
    amount: Decimal
    currency: str
    description: str = ""


@dataclass
class InstrumentInfo:
    symbol: str
    description: str = ""
    isin: str = ""
    asset_category: str = ""
    country: str = ""


@dataclass
class NavSummary:
    prior_total: Decimal = Decimal("0")
    current_total: Decimal = Decimal("0")
    change: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")
    stock: Decimal = Decimal("0")
    dividend_accruals: Decimal = Decimal("0")


@dataclass
class ChangeInNav:
    starting_value: Decimal = Decimal("0")
    ending_value: Decimal = Decimal("0")
    change: Decimal = Decimal("0")


@dataclass
class StatementData:
    meta: StatementMeta = field(default_factory=StatementMeta)
    positions: list[Position] = field(default_factory=list)
    cash_balances: list[CashBalance] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    dividends: list[Dividend] = field(default_factory=list)
    withholding_taxes: list[WithholdingTax] = field(default_factory=list)
    deposits_withdrawals: list[DepositWithdrawal] = field(default_factory=list)
    instruments: dict[str, InstrumentInfo] = field(default_factory=dict)
    nav: NavSummary = field(default_factory=NavSummary)
    change_in_nav: ChangeInNav = field(default_factory=ChangeInNav)


def parse_ibkr_datetime(value: str) -> date:
    """Parse IBKR date/time strings like '2025-03-15, 10:30:00' or '2025-03-15'."""
    value = value.strip().strip('"')
    if not value or value == "-":
        raise ValueError(f"empty date: {value!r}")
    date_part = value.split(",")[0].strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: {value!r}")


def parse_decimal(value: str) -> Decimal:
    value = value.strip().strip('"')
    if not value or value == "-":
        return Decimal("0")
    return Decimal(value.replace(",", ""))

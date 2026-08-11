"""Parse IBKR Activity Statement CSV files."""

from __future__ import annotations

import csv
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .models import (
    CashBalance,
    ChangeInNav,
    DepositWithdrawal,
    Dividend,
    InstrumentInfo,
    NavSummary,
    Position,
    StatementData,
    StatementMeta,
    Trade,
    WithholdingTax,
    parse_decimal,
    parse_ibkr_datetime,
)

STOCK_CATEGORIES = {"Stocks", "Equity and Index Options", "Warrants", "REITs"}


def _split_sections(rows: list[list[str]]) -> dict[str, list[list[str]]]:
    sections: dict[str, list[list[str]]] = {}
    for row in rows:
        if not row:
            continue
        section = row[0].strip().strip('"')
        sections.setdefault(section, []).append(row)
    return sections


def _header_map(section_rows: list[list[str]]) -> dict[str, int]:
    for row in section_rows:
        if len(row) >= 2 and row[1] == "Header":
            return {col.strip(): i for i, col in enumerate(row)}
    return {}


def _get(row: list[str], header: dict[str, int], col: str, default: str = "") -> str:
    idx = header.get(col)
    if idx is None or idx >= len(row):
        return default
    return row[idx].strip().strip('"')


def _parse_period(period_text: str) -> tuple[date | None, date | None]:
    match = re.search(
        r"([A-Za-z]+ \d{1,2}, \d{4})\s*-\s*([A-Za-z]+ \d{1,2}, \d{4})",
        period_text,
    )
    if not match:
        return None, None
    start = datetime.strptime(match.group(1), "%B %d, %Y").date()
    end = datetime.strptime(match.group(2), "%B %d, %Y").date()
    return start, end


def _parse_statement_meta(section_rows: list[list[str]]) -> StatementMeta:
    meta = StatementMeta()
    for row in section_rows:
        if len(row) < 4 or row[1] != "Data":
            continue
        field_name = row[2].strip()
        field_value = row[3].strip().strip('"')
        if field_name == "Period":
            meta.period_start, meta.period_end = _parse_period(field_value)
        elif field_name == "Base Currency":
            meta.base_currency = field_value or meta.base_currency
        elif field_name in {"Account", "Account ID", "ClientAccountID"}:
            meta.account_id = field_value
    return meta


def _parse_open_positions(section_rows: list[list[str]]) -> list[Position]:
    header = _header_map(section_rows)
    positions: list[Position] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        discriminator = _get(row, header, "DataDiscriminator")
        asset_category = _get(row, header, "Asset Category")
        if discriminator not in {"", "Summary"}:
            continue
        if asset_category not in STOCK_CATEGORIES:
            continue
        symbol = _get(row, header, "Symbol")
        if not symbol or symbol == "Total":
            continue
        quantity = parse_decimal(_get(row, header, "Quantity"))
        if quantity == 0:
            continue
        positions.append(
            Position(
                symbol=symbol,
                quantity=quantity,
                close_price=parse_decimal(_get(row, header, "Close Price")),
                value=parse_decimal(_get(row, header, "Value")),
                currency=_get(row, header, "Currency", "USD"),
                asset_category=asset_category,
                cost_basis=parse_decimal(_get(row, header, "Cost Basis")),
            )
        )
    return positions


def _parse_forex_balances(section_rows: list[list[str]]) -> list[CashBalance]:
    header = _header_map(section_rows)
    balances: list[CashBalance] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        asset_category = _get(row, header, "Asset Category")
        if asset_category in {"Total", ""}:
            continue
        description = _get(row, header, "Description")
        quantity = parse_decimal(_get(row, header, "Quantity"))
        value_usd = parse_decimal(_get(row, header, "Value in USD"))
        if description.upper() == "USD":
            balances.append(CashBalance(currency="USD", ending_cash=quantity))
        elif value_usd != 0:
            balances.append(
                CashBalance(
                    currency=description,
                    ending_cash=value_usd,
                    description=f"Forex {description}",
                )
            )
    return balances


def _parse_fx_rates(forex_rows: list[list[str]], position_rows: list[list[str]]) -> dict[str, Decimal]:
    """Build FX rates to USD from Forex Balances and Open Positions totals."""
    rates: dict[str, Decimal] = {"USD": Decimal("1")}
    header = _header_map(forex_rows)
    for row in forex_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        description = _get(row, header, "Description")
        close = _get(row, header, "Close Price")
        if description and close and description.upper() != "USD":
            rates[description] = parse_decimal(close)

    pos_header = _header_map(position_rows)
    pending_ccy: str | None = None
    pending_value: Decimal | None = None
    for row in position_rows:
        if len(row) < 2 or row[1] != "Total":
            continue
        asset = _get(row, pos_header, "Asset Category")
        if asset != "Stocks":
            continue
        currency = _get(row, pos_header, "Currency")
        value = parse_decimal(_get(row, pos_header, "Value"))
        if currency in {"EUR", "GBP", "SEK", "CHF", "CAD", "AUD", "JPY"}:
            pending_ccy = currency
            pending_value = value
        elif currency == "USD" and pending_ccy and pending_value and pending_value != 0:
            rates[pending_ccy] = value / pending_value
            pending_ccy = None
            pending_value = None
    return rates


def _convert_positions_to_usd(
    positions: list[Position], fx_rates: dict[str, Decimal]
) -> None:
    for position in positions:
        if position.currency == "USD":
            continue
        rate = fx_rates.get(position.currency)
        if rate:
            position.value = (position.value * rate).quantize(Decimal("0.000001"))


def _parse_cash_report(section_rows: list[list[str]]) -> list[CashBalance]:
    balances: list[CashBalance] = []
    for row in section_rows:
        if len(row) < 5 or row[1] != "Data":
            continue
        field_name = row[2].strip()
        if field_name != "Ending Cash":
            continue
        currency = row[3].strip()
        if not currency or currency == "Base Currency Summary":
            continue
        ending = parse_decimal(row[4])
        balances.append(CashBalance(currency=currency, ending_cash=ending))
    return balances


def _parse_trades(section_rows: list[list[str]]) -> list[Trade]:
    header = _header_map(section_rows)
    trades: list[Trade] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        if _get(row, header, "DataDiscriminator") != "Order":
            continue
        asset_category = _get(row, header, "Asset Category")
        if asset_category == "Forex":
            continue
        if asset_category not in STOCK_CATEGORIES:
            continue
        symbol = _get(row, header, "Symbol")
        dt_str = _get(row, header, "Date/Time")
        if not symbol or not dt_str:
            continue
        try:
            trade_date = parse_ibkr_datetime(dt_str)
        except ValueError:
            continue
        trades.append(
            Trade(
                symbol=symbol,
                date=trade_date,
                quantity=parse_decimal(_get(row, header, "Quantity")),
                price=parse_decimal(_get(row, header, "T. Price")),
                proceeds=parse_decimal(_get(row, header, "Proceeds")),
                commission=parse_decimal(_get(row, header, "Comm/Fee")),
                basis=parse_decimal(_get(row, header, "Basis")),
                realized_pl=parse_decimal(_get(row, header, "Realized P/L")),
                currency=_get(row, header, "Currency", "USD"),
                asset_category=asset_category,
                code=_get(row, header, "Code"),
            )
        )
    return trades


def _parse_dividends(section_rows: list[list[str]]) -> list[Dividend]:
    header = _header_map(section_rows)
    dividends: list[Dividend] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        dt_str = _get(row, header, "Date")
        amount_str = _get(row, header, "Amount")
        if not dt_str or not amount_str:
            continue
        description = _get(row, header, "Description")
        symbol = _extract_symbol(description)
        try:
            div_date = parse_ibkr_datetime(dt_str)
        except ValueError:
            continue
        dividends.append(
            Dividend(
                symbol=symbol,
                date=div_date,
                amount=parse_decimal(amount_str),
                currency=_get(row, header, "Currency", "USD"),
                description=description,
            )
        )
    return dividends


def _parse_withholding(section_rows: list[list[str]]) -> list[WithholdingTax]:
    header = _header_map(section_rows)
    items: list[WithholdingTax] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        dt_str = _get(row, header, "Date")
        amount_str = _get(row, header, "Amount")
        if not dt_str or not amount_str:
            continue
        description = _get(row, header, "Description")
        try:
            tax_date = parse_ibkr_datetime(dt_str)
        except ValueError:
            continue
        items.append(
            WithholdingTax(
                symbol=_extract_symbol(description),
                date=tax_date,
                amount=parse_decimal(amount_str),
                currency=_get(row, header, "Currency", "USD"),
                description=description,
            )
        )
    return items


def _parse_deposits(section_rows: list[list[str]]) -> list[DepositWithdrawal]:
    header = _header_map(section_rows)
    items: list[DepositWithdrawal] = []
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        dt_str = _get(row, header, "Date", _get(row, header, "Settle Date"))
        amount_str = _get(row, header, "Amount")
        if not dt_str or not amount_str:
            continue
        try:
            dw_date = parse_ibkr_datetime(dt_str)
        except ValueError:
            continue
        items.append(
            DepositWithdrawal(
                date=dw_date,
                amount=parse_decimal(amount_str),
                currency=_get(row, header, "Currency", "USD"),
                description=_get(row, header, "Description"),
            )
        )
    return items


def _parse_instruments(section_rows: list[list[str]]) -> dict[str, InstrumentInfo]:
    header = _header_map(section_rows)
    instruments: dict[str, InstrumentInfo] = {}
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        symbol = _get(row, header, "Symbol")
        if not symbol:
            continue
        instruments[symbol] = InstrumentInfo(
            symbol=symbol,
            description=_get(row, header, "Description"),
            isin=_get(row, header, "Security ID", _get(row, header, "ISIN")),
            asset_category=_get(row, header, "Asset Category"),
            country=_get(row, header, "Country", _get(row, header, "Listing Exchange")),
        )
    return instruments


def _parse_nav(section_rows: list[list[str]]) -> NavSummary:
    header = _header_map(section_rows)
    nav = NavSummary()
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        asset_class = _get(row, header, "Asset Class").strip().lower()
        current = parse_decimal(_get(row, header, "Current Total"))
        if asset_class == "total":
            nav.prior_total = parse_decimal(_get(row, header, "Prior Total"))
            nav.current_total = current
            nav.change = parse_decimal(_get(row, header, "Change"))
        elif asset_class == "cash":
            nav.cash = current
        elif asset_class == "stock":
            nav.stock = current
        elif asset_class == "dividend accruals":
            nav.dividend_accruals = current
    return nav


def _parse_change_in_nav(section_rows: list[list[str]]) -> ChangeInNav:
    header = _header_map(section_rows)
    change = ChangeInNav()
    for row in section_rows:
        if len(row) < 2 or row[1] != "Data":
            continue
        field_name = _get(row, header, "Field Name", _get(row, header, "Header"))
        if field_name in {"", "Header"}:
            # Some statements use a single summary row
            starting = parse_decimal(_get(row, header, "Starting Value"))
            ending = parse_decimal(_get(row, header, "Ending Value"))
            if starting or ending:
                change.starting_value = starting
                change.ending_value = ending
                change.change = parse_decimal(_get(row, header, "Change"))
            continue
        if field_name == "Starting Value":
            change.starting_value = parse_decimal(_get(row, header, "Field Value", row[-1]))
        elif field_name == "Ending Value":
            change.ending_value = parse_decimal(_get(row, header, "Field Value", row[-1]))
        elif field_name == "Change":
            change.change = parse_decimal(_get(row, header, "Field Value", row[-1]))
    return change


def _extract_symbol(description: str) -> str:
    if not description:
        return ""
    token = description.split("(")[0].strip()
    return token.split()[0] if token else ""


def parse_statement(path: str | Path) -> StatementData:
    """Parse an IBKR Activity Statement CSV into structured data."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = [row for row in reader if row]

    sections = _split_sections(rows)
    statement = StatementData()

    if "Statement" in sections:
        statement.meta = _parse_statement_meta(sections["Statement"])

    if "Open Positions" in sections:
        statement.positions = _parse_open_positions(sections["Open Positions"])
        fx_rates = _parse_fx_rates(
            sections.get("Forex Balances", []),
            sections["Open Positions"],
        )
        _convert_positions_to_usd(statement.positions, fx_rates)

    forex = _parse_forex_balances(sections.get("Forex Balances", []))
    cash_report = _parse_cash_report(sections.get("Cash Report", []))
    statement.cash_balances = forex or cash_report

    if "Trades" in sections:
        statement.trades = _parse_trades(sections["Trades"])

    if "Dividends" in sections:
        statement.dividends = _parse_dividends(sections["Dividends"])

    if "Withholding Tax" in sections:
        statement.withholding_taxes = _parse_withholding(sections["Withholding Tax"])

    if "Deposits & Withdrawals" in sections:
        statement.deposits_withdrawals = _parse_deposits(sections["Deposits & Withdrawals"])

    if "Financial Instrument Information" in sections:
        statement.instruments = _parse_instruments(sections["Financial Instrument Information"])

    if "Net Asset Value" in sections:
        statement.nav = _parse_nav(sections["Net Asset Value"])

    if "Change in NAV" in sections:
        statement.change_in_nav = _parse_change_in_nav(sections["Change in NAV"])

    _enrich_positions(statement)
    return statement


def _enrich_positions(statement: StatementData) -> None:
    for position in statement.positions:
        info = statement.instruments.get(position.symbol)
        if not info:
            continue
        position.isin = info.isin or position.isin
        position.country = info.country or position.country


def filter_by_year(statement: StatementData, year: int) -> StatementData:
    """Return a copy with trades/dividends filtered to the target calendar year."""
    filtered = StatementData(
        meta=statement.meta,
        positions=list(statement.positions),
        cash_balances=list(statement.cash_balances),
        trades=[t for t in statement.trades if t.date.year == year],
        dividends=[d for d in statement.dividends if d.date.year == year],
        withholding_taxes=[w for w in statement.withholding_taxes if w.date.year == year],
        deposits_withdrawals=[
            d for d in statement.deposits_withdrawals if d.date.year == year
        ],
        instruments=dict(statement.instruments),
        nav=statement.nav,
        change_in_nav=statement.change_in_nav,
    )
    return filtered

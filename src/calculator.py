"""IRPF calculations: Bens e Direitos, dividends, capital gains."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .models import StatementData
from .parser import filter_by_year, parse_statement
from .prices import cash_value_brl, position_value_brl, statement_end_date, total_portfolio_usd


@dataclass
class BensDireitosItem:
    symbol: str
    country: str
    quantity: Decimal
    value_usd: Decimal
    value_brl: Decimal
    prior_brl: Decimal
    isin: str
    description: str


@dataclass
class DividendItem:
    symbol: str
    date: date
    amount_usd: Decimal
    ptax: Decimal
    amount_brl: Decimal
    description: str


@dataclass
class CapitalGainSale:
    symbol: str
    date: date
    quantity: Decimal
    proceeds_usd: Decimal
    proceeds_brl: Decimal
    cost_brl: Decimal
    gain_brl: Decimal
    ptax: Decimal


@dataclass
class MonthlySaleCheck:
    year_month: str
    proceeds_brl: Decimal
    needs_darf: bool


@dataclass
class CbeCheck:
    nav_usd: Decimal
    deposits_usd: Decimal
    cbe_required: bool
    reason: str


@dataclass
class IrpfReport:
    year: int
    valuation_date: date
    bens_direitos: list[BensDireitosItem] = field(default_factory=list)
    cash_brl: Decimal = Decimal("0")
    dividends: list[DividendItem] = field(default_factory=list)
    capital_gains: list[CapitalGainSale] = field(default_factory=list)
    monthly_sales: list[MonthlySaleCheck] = field(default_factory=list)
    total_dividends_brl: Decimal = Decimal("0")
    total_capital_gain_brl: Decimal = Decimal("0")
    cbe: CbeCheck | None = None
    prior_year_source: str = ""
    validation_notes: list[str] = field(default_factory=list)
    is_first_ibkr_year: bool = False


DARF_THRESHOLD_BRL = Decimal("35000")
CBE_THRESHOLD_USD = Decimal("100000")


def _country_label(position_country: str, symbol: str) -> str:
    if position_country:
        return position_country
    if symbol.endswith(".L"):
        return "Reino Unido"
    if symbol.endswith(".PA"):
        return "França"
    return "EUA"


def _discrimination(item: BensDireitosItem) -> str:
    qty = item.quantity.normalize()
    qty_text = f"{qty:f}".rstrip("0").rstrip(".")
    base = f"Interactive Brokers LLC - {item.country} - {item.symbol} - {qty_text} ações"
    if item.isin:
        return f"{base} (ISIN {item.isin})"
    return base


def load_prior_year_json(path: Path, year: int) -> dict[str, Decimal] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("year") != year - 1:
        return None
    positions = data.get("positions", {})
    return {symbol: Decimal(str(value)) for symbol, value in positions.items()}


def save_year_json(report: IrpfReport, path: Path) -> None:
    payload = {
        "year": report.year,
        "valuation_date": report.valuation_date.isoformat(),
        "positions": {
            item.symbol: str(item.value_brl) for item in report.bens_direitos
        },
        "cash_brl": str(report.cash_brl),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _compute_custo_medio_gains(
    trades: list,
    ptax_lookup: Callable[[date], Decimal],
) -> list[CapitalGainSale]:
    """Average-cost capital gains in BRL (Brazilian PF rules, not IBKR FIFO)."""
    lots: dict[str, tuple[Decimal, Decimal]] = {}  # symbol -> (qty, total_cost_brl)
    sales: list[CapitalGainSale] = []

    for trade in sorted(trades, key=lambda t: (t.date, t.symbol)):
        if trade.quantity == 0:
            continue
        symbol = trade.symbol
        ptax = ptax_lookup(trade.date)

        if trade.quantity > 0:
            cost_brl = abs(trade.proceeds + trade.commission) * ptax
            qty, total_cost = lots.get(symbol, (Decimal("0"), Decimal("0")))
            lots[symbol] = (qty + trade.quantity, total_cost + cost_brl)
            continue

        sell_qty = abs(trade.quantity)
        qty, total_cost = lots.get(symbol, (Decimal("0"), Decimal("0")))
        if qty <= 0:
            avg_cost = Decimal("0")
        else:
            avg_cost = total_cost / qty

        cost_brl = (avg_cost * sell_qty).quantize(Decimal("0.01"))
        proceeds_brl = (trade.proceeds * ptax).quantize(Decimal("0.01"))
        gain_brl = (proceeds_brl - cost_brl).quantize(Decimal("0.01"))

        remaining_qty = max(qty - sell_qty, Decimal("0"))
        remaining_cost = max(total_cost - cost_brl, Decimal("0"))
        lots[symbol] = (remaining_qty, remaining_cost)

        sales.append(
            CapitalGainSale(
                symbol=symbol,
                date=trade.date,
                quantity=sell_qty,
                proceeds_usd=trade.proceeds,
                proceeds_brl=proceeds_brl,
                cost_brl=cost_brl,
                gain_brl=gain_brl,
                ptax=ptax,
            )
        )

    return sales


def compute_irpf(
    statement: StatementData,
    year: int,
    ptax_lookup: Callable[[date], Decimal],
    prior_positions_brl: dict[str, Decimal] | None = None,
) -> IrpfReport:
    filtered = filter_by_year(statement, year)
    valuation_date = statement_end_date(statement, year)
    end_ptax = ptax_lookup(valuation_date)

    is_first_year = statement.nav.prior_total == 0
    prior_source = "json" if prior_positions_brl else "nav_zero" if is_first_year else "missing"

    report = IrpfReport(
        year=year,
        valuation_date=valuation_date,
        is_first_ibkr_year=is_first_year,
        prior_year_source=prior_source,
    )

    for position in statement.positions:
        prior_brl = Decimal("0")
        if prior_positions_brl and position.symbol in prior_positions_brl:
            prior_brl = prior_positions_brl[position.symbol]
        elif is_first_year:
            prior_brl = Decimal("0")

        value_brl = position_value_brl(position, valuation_date, ptax_lookup)
        report.bens_direitos.append(
            BensDireitosItem(
                symbol=position.symbol,
                country=_country_label(position.country, position.symbol),
                quantity=position.quantity,
                value_usd=position.value,
                value_brl=value_brl,
                prior_brl=prior_brl,
                isin=position.isin,
                description=_discrimination(
                    BensDireitosItem(
                        symbol=position.symbol,
                        country=_country_label(position.country, position.symbol),
                        quantity=position.quantity,
                        value_usd=position.value,
                        value_brl=value_brl,
                        prior_brl=prior_brl,
                        isin=position.isin,
                        description="",
                    )
                ),
            )
        )

    report.cash_brl = sum(
        (cash_value_brl(b, valuation_date, ptax_lookup) for b in statement.cash_balances),
        Decimal("0"),
    )

    for dividend in filtered.dividends:
        ptax = ptax_lookup(dividend.date)
        amount_brl = (dividend.amount * ptax).quantize(Decimal("0.01"))
        report.dividends.append(
            DividendItem(
                symbol=dividend.symbol,
                date=dividend.date,
                amount_usd=dividend.amount,
                ptax=ptax,
                amount_brl=amount_brl,
                description=dividend.description,
            )
        )
        report.total_dividends_brl += amount_brl

    report.capital_gains = _compute_custo_medio_gains(filtered.trades, ptax_lookup)
    report.total_capital_gain_brl = sum(
        (s.gain_brl for s in report.capital_gains), Decimal("0")
    )

    monthly: dict[str, Decimal] = {}
    for sale in report.capital_gains:
        key = sale.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, Decimal("0")) + sale.proceeds_brl

    for year_month, proceeds in sorted(monthly.items()):
        report.monthly_sales.append(
            MonthlySaleCheck(
                year_month=year_month,
                proceeds_brl=proceeds,
                needs_darf=proceeds > DARF_THRESHOLD_BRL,
            )
        )

    nav_usd = total_portfolio_usd(statement)
    deposits_usd = sum(
        (d.amount for d in filtered.deposits_withdrawals if d.amount > 0),
        Decimal("0"),
    )
    cbe_required = nav_usd >= CBE_THRESHOLD_USD or deposits_usd >= CBE_THRESHOLD_USD
    reason = []
    if nav_usd >= CBE_THRESHOLD_USD:
        reason.append(f"NAV USD {nav_usd:,.2f} ≥ USD 100.000")
    if deposits_usd >= CBE_THRESHOLD_USD:
        reason.append(f"remessas USD {deposits_usd:,.2f} ≥ USD 100.000")
    report.cbe = CbeCheck(
        nav_usd=nav_usd,
        deposits_usd=deposits_usd,
        cbe_required=cbe_required,
        reason="; ".join(reason) if reason else "abaixo dos limites informativos",
    )

    _validate(statement, report, end_ptax)
    return report


def _validate(statement: StatementData, report: IrpfReport, end_ptax: Decimal) -> None:
    computed_usd = total_portfolio_usd(statement)
    if statement.change_in_nav.ending_value and computed_usd:
        diff = abs(statement.change_in_nav.ending_value - computed_usd)
        if diff > Decimal("1"):
            report.validation_notes.append(
                f"Open Positions + Cash ({computed_usd}) diverge de Change in NAV "
                f"Ending Value ({statement.change_in_nav.ending_value}) em USD {diff}."
            )

    if not report.bens_direitos and not report.cash_brl:
        report.validation_notes.append("Nenhuma posição ou caixa encontrada no extrato.")

    if end_ptax <= 0:
        report.validation_notes.append("PTAX da data de fechamento inválida.")


def resolve_prior_year(
    statement: StatementData,
    year: int,
    prior_json_path: Path | None,
    prior_statement_path: Path | None,
    ptax_lookup: Callable[[date], Decimal],
) -> dict[str, Decimal] | None:
    if prior_json_path:
        prior = load_prior_year_json(prior_json_path, year)
        if prior:
            return prior

    if prior_statement_path:
        prior_stmt = parse_statement(prior_statement_path)
        prior_year = year - 1
        prior_date = statement_end_date(prior_stmt, prior_year)
        return {
            p.symbol: position_value_brl(p, prior_date, ptax_lookup)
            for p in prior_stmt.positions
        }

    if statement.nav.prior_total == 0:
        return {}

    return None

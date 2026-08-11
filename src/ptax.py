"""Fetch and cache BCB PTAX (USD/BRL) rates."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

import requests

PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@dataCotacao)"
    "?@dataCotacao='{date_str}'&$format=json"
)


class PtaxClient:
    """PTAX lookup with optional on-disk cache."""

    def __init__(self, cache_dir: Path | None = None, session: requests.Session | None = None):
        self.cache_dir = cache_dir or Path("cache/ptax")
        self.session = session or requests.Session()
        self._memory: dict[date, Decimal] = {}

    def get(self, target_date: date) -> Decimal:
        if target_date in self._memory:
            return self._memory[target_date]

        cached = self._read_cache(target_date)
        if cached is not None:
            self._memory[target_date] = cached
            return cached

        rate = self._fetch_with_fallback(target_date)
        self._memory[target_date] = rate
        self._write_cache(target_date, rate)
        return rate

    def get_many(self, dates: set[date]) -> dict[date, Decimal]:
        return {d: self.get(d) for d in sorted(dates)}

    def _fetch_with_fallback(self, target_date: date) -> Decimal:
        current = target_date
        for _ in range(10):
            rate = self._fetch_day(current)
            if rate is not None:
                return rate
            current -= timedelta(days=1)
        raise RuntimeError(f"PTAX not found for {target_date} (or prior 10 business days)")

    def _fetch_day(self, target_date: date) -> Decimal | None:
        date_str = target_date.strftime("%m-%d-%Y")
        response = self.session.get(PTAX_URL.format(date_str=date_str), timeout=30)
        response.raise_for_status()
        payload = response.json()
        values = payload.get("value", [])
        if not values:
            return None
        # Use selling rate (cotacaoVenda) — standard for IRPF conversions
        return Decimal(str(values[-1]["cotacaoVenda"]))

    def _cache_path(self, target_date: date) -> Path:
        return self.cache_dir / f"{target_date.isoformat()}.json"

    def _read_cache(self, target_date: date) -> Decimal | None:
        path = self._cache_path(target_date)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Decimal(str(data["rate"]))

    def _write_cache(self, target_date: date, rate: Decimal) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(target_date)
        path.write_text(
            json.dumps({"date": target_date.isoformat(), "rate": str(rate)}, indent=2),
            encoding="utf-8",
        )


def make_ptax_lookup(
    cache_dir: Path | None = None,
    overrides: dict[date, Decimal] | None = None,
) -> Callable[[date], Decimal]:
    """Return a date→rate function, with optional fixed overrides for tests."""
    client = PtaxClient(cache_dir=cache_dir)
    overrides = overrides or {}

    def lookup(target_date: date) -> Decimal:
        if target_date in overrides:
            return overrides[target_date]
        return client.get(target_date)

    return lookup

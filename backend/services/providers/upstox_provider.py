"""Upstox historical OHLCV provider behind the MarketDataProvider boundary.

MD-02 makes Upstox *technically available* as a market-data provider.  It is
NOT wired as the production primary (Yahoo remains primary, Seed remains the
fallback).  This provider currently implements only the historical OHLCV part
of the ``MarketDataProvider`` contract; the remaining legacy-catalogue
operations raise ``NotImplementedError`` so the existing MarketDataService
fallback to the seed catalogue applies for those reads.

All Upstox-specific concerns stay inside this module and its instrument-mapping
seam:

- Upstox Historical Candle V3 request construction (``unit``/``interval`` and
  absolute ``YYYY-MM-DD`` dates vs the app's relative Yahoo-style ``period``).
- Bearer access-token authentication.
- Parsing of the Upstox candle JSON and conversion to ``OHLCVBar``.
- Instrument-key resolution (delegated to ``UpstoxInstrumentMapper``).

No consumer imports or knows about Upstox JSON, HTTP details, or instrument
keys; consumers talk to ``MarketDataProvider`` / ``MarketDataService`` only.
"""
from __future__ import annotations

import logging
import math
import os
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote

import requests

from services.market_data.models import OHLCVBar
from services.market_data_provider import MarketDataProvider
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper

logger = logging.getLogger("tradelens.market_data.upstox")

_DEFAULT_BASE_URL = "https://api.upstox.com"
_DEFAULT_TIMEOUT_SECONDS = 10.0

_ACCESS_TOKEN_ENV = "UPSTOX_ACCESS_TOKEN"
_BASE_URL_ENV = "UPSTOX_BASE_URL"

CandleFetcher = Callable[[str, dict[str, str], float], Any]

# App interval strings -> (Upstox unit, Upstox interval).
_UPSTOX_INTERVALS: dict[str, tuple[str, str]] = {
    "1d": ("days", "1"),
    "5m": ("minutes", "5"),
    "10m": ("minutes", "10"),
    "15m": ("minutes", "15"),
    "30m": ("minutes", "30"),
    "1h": ("hours", "1"),
}


def _access_token_from_env() -> str:
    return os.environ.get(_ACCESS_TOKEN_ENV, "")


def _base_url_from_env() -> str:
    return os.environ.get(_BASE_URL_ENV, "").strip() or _DEFAULT_BASE_URL


def _default_fetch(url: str, headers: dict[str, str], timeout: float) -> Any:
    """Default HTTP GET for the Upstox Historical Candle V3 endpoint."""
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response


def _as_payload(body: Any) -> dict[str, Any]:
    """Normalize a fetcher result (``requests.Response`` or a parsed body)."""
    if hasattr(body, "json"):
        try:
            body = body.json()
        except Exception as exc:
            raise RuntimeError(f"Upstox response is not valid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise RuntimeError("Upstox response is not a JSON object")
    return body


def _sub_months(value: date, months: int) -> date:
    total_months = value.year * 12 + (value.month - 1) - months
    year, month_index = divmod(total_months, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


class UpstoxMarketDataProvider(MarketDataProvider):
    """Read historical OHLCV candles from Upstox Historical Candle V3.

    The provider accepts normalized application symbols.  Each symbol is
    resolved to an Upstox ``instrument_key`` through a small explicit mapping
    seam; unmapped symbols fail clearly so the MarketDataService fallback path
    applies.
    """

    name = "upstox"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        instrument_mapper: UpstoxInstrumentMapper | None = None,
        fetcher: CandleFetcher | None = None,
        request_timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        now: Callable[[], datetime] | None = None,
    ):
        self._access_token = (
            access_token if access_token is not None else _access_token_from_env()
        )
        self._base_url = (base_url or _base_url_from_env()).rstrip("/")
        self._instrument_mapper = instrument_mapper or UpstoxInstrumentMapper()
        self._fetcher = fetcher or _default_fetch
        self._request_timeout = request_timeout
        self._now = now or (lambda: datetime.now(timezone.utc))

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        normalized = symbol.strip().upper()
        instrument_key = self._instrument_mapper.to_instrument_key(normalized)
        unit, candle_interval = self._translate_interval(interval)
        from_date, to_date = self._translate_period(period)
        url = self._build_url(instrument_key, unit, candle_interval, from_date, to_date)
        headers = self._build_headers()
        payload = self._fetch_json(url, headers)
        candles = self._extract_candles(payload)
        bars = [self._candle_to_bar(candle) for candle in candles]
        logger.info(
            "fetched %d Upstox candles for %s (%s/%s)",
            len(bars),
            normalized,
            interval,
            period,
        )
        return bars

    def get_market_summary(self) -> dict[str, Any]:
        return self._unsupported("get_market_summary")

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        return self._unsupported("get_stock")  # type: ignore[return-value]

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        return self._unsupported("get_stock_insight")

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._unsupported("search_stocks")  # type: ignore[return-value]

    def get_opportunities(self) -> list[dict[str, Any]]:
        return self._unsupported("get_opportunities")  # type: ignore[return-value]

    def get_all_stocks(self) -> list[dict[str, Any]]:
        return self._unsupported("get_all_stocks")  # type: ignore[return-value]

    def get_default_watchlist_symbols(self) -> list[str]:
        return self._unsupported("get_default_watchlist_symbols")  # type: ignore[return-value]

    def _unsupported(self, operation: str) -> Any:
        raise NotImplementedError(
            f"UpstoxMarketDataProvider currently supports historical OHLCV only; "
            f"{operation} is not implemented for Upstox"
        )

    def _build_headers(self) -> dict[str, str]:
        if not self._access_token:
            raise RuntimeError(
                f"Upstox access token is not configured ({_ACCESS_TOKEN_ENV})"
            )
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }

    def _translate_interval(self, interval: str) -> tuple[str, str]:
        key = str(interval).strip().lower()
        resolved = _UPSTOX_INTERVALS.get(key)
        if resolved is None:
            raise RuntimeError(f"unsupported Upstox interval {interval!r}")
        return resolved

    def _translate_period(self, period: str) -> tuple[date, date]:
        to_date = self._now().date()
        token = str(period).strip().lower()
        if token.endswith("mo"):
            months = _parse_positive_int(token[:-2], "period", period)
            from_date = _sub_months(to_date, months)
        elif token.endswith("y"):
            years = _parse_positive_int(token[:-1], "period", period)
            from_date = _sub_months(to_date, years * 12)
        elif token.endswith("d"):
            days = _parse_positive_int(token[:-1], "period", period)
            from_date = to_date - timedelta(days=days)
        else:
            raise RuntimeError(f"unsupported Upstox period {period!r}")
        return from_date, to_date

    def _build_url(
        self,
        instrument_key: str,
        unit: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> str:
        encoded_key = quote(instrument_key, safe="")
        return (
            f"{self._base_url}/v3/historical-candle/{encoded_key}/"
            f"{unit}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        )

    def _fetch_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        try:
            body = self._fetcher(url, headers, self._request_timeout)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Upstox historical candle request failed for {url}: {exc}"
            ) from exc
        return _as_payload(body)

    @staticmethod
    def _extract_candles(payload: dict[str, Any]) -> list[Any]:
        if payload.get("status") == "error":
            message = payload.get("message", "unknown error")
            raise RuntimeError(f"Upstox API error: {message}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Upstox response is missing the 'data' object")
        candles = data.get("candles")
        if candles is None:
            raise RuntimeError("Upstox response is missing 'data.candles'")
        if not isinstance(candles, list):
            raise RuntimeError("Upstox 'data.candles' is not a list")
        return candles

    @staticmethod
    def _candle_to_bar(candle: Any) -> OHLCVBar:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            raise RuntimeError(f"Upstox candle has an invalid shape: {candle!r}")

        try:
            timestamp = datetime.fromisoformat(str(candle[0]))
        except ValueError as exc:
            raise RuntimeError(
                f"Upstox candle has an invalid timestamp: {candle[0]!r}"
            ) from exc

        ohlc: list[float] = []
        for label, raw in (
            ("open", candle[1]),
            ("high", candle[2]),
            ("low", candle[3]),
            ("close", candle[4]),
        ):
            try:
                number = float(raw)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Upstox candle {label} is not a number: {raw!r}"
                ) from exc
            if not math.isfinite(number):
                raise RuntimeError(f"Upstox candle {label} is not finite: {raw!r}")
            ohlc.append(number)

        raw_volume = candle[5]
        try:
            volume = float(raw_volume) if raw_volume is not None else None
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Upstox candle volume is not a number: {raw_volume!r}") from exc

        try:
            return OHLCVBar(
                timestamp=timestamp,
                open=ohlc[0],
                high=ohlc[1],
                low=ohlc[2],
                close=ohlc[3],
                volume=volume,
            )
        except ValueError as exc:
            raise RuntimeError(f"Upstox candle produced an invalid bar: {exc}") from exc


def _parse_positive_int(raw: str, label: str, value: object) -> int:
    try:
        number = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"unsupported Upstox {label} {value!r}") from exc
    if number <= 0:
        raise RuntimeError(f"unsupported Upstox {label} {value!r}")
    return number
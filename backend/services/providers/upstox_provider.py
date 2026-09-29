"""Upstox market data provider behind the MarketDataProvider boundary.

MD-02 added the historical OHLCV part of the ``MarketDataProvider`` contract.
MD-03 completes the contract with live LTP quotes and OHLCV-derived snapshot
and insight reads, and wires Upstox as an *optional* production primary behind
the existing MarketDataService (chain: Upstox -> Yahoo -> Seed).  Catalogue-only
operations (search, opportunities, all-stocks, watchlist) remain
``NotImplementedError`` so the MarketDataService chain delegates them to the
seed catalogue.

All Upstox-specific concerns stay inside this module and its instrument-mapping
seam:

- Upstox Historical Candle V3 request construction (``unit``/``interval`` and
  absolute ``YYYY-MM-DD`` dates vs the app's relative Yahoo-style ``period``),
  including Upstox's intraday lookback caps (1-15 minute candles = 28 days;
  30+ minute and hourly candles = 90 days).
- Bearer access-token authentication and the live LTP quote
  (``/v2/market-quote/ltp``).
- Parsing of the Upstox candle / quote JSON and conversion to ``OHLCVBar``.
- Instrument-key resolution (delegated to ``UpstoxInstrumentMapper``).

Price semantics follow ADR-003: the snapshot ``price`` is the live LTP quote
from Upstox (never a daily close), ``changePct`` is measured against the
Upstox previous close, and all indicators (RSI/EMA/VWAP/support/resistance)
derive from the same Upstox OHLCV bars as the charts.  Catalogue metadata
(name, sector, score, trend, day-high, average volume) stays seeded.

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
from zoneinfo import ZoneInfo

import requests

from services.market_data.indicators import (
    calculate_latest_ema,
    calculate_latest_rsi,
    calculate_rolling_vwap,
)
from services.market_data.models import (
    Instrument,
    MarketQuote,
    OHLCVBar,
    Quote,
    StockInsight,
)
from services.market_data.snapshot_builder import (
    build_legacy_insight_dict,
    build_legacy_stock_from_quote,
)
from services.market_data_provider import MarketDataProvider, ProviderRateLimitedError
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
from services.symbol_mapper import SymbolMapper

logger = logging.getLogger("tradelens.market_data.upstox")

_DEFAULT_BASE_URL = "https://api.upstox.com"
_DEFAULT_TIMEOUT_SECONDS = 10.0

_HTTP_TOO_MANY_REQUESTS = 429

_ACCESS_TOKEN_ENV = "UPSTOX_ACCESS_TOKEN"
_BASE_URL_ENV = "UPSTOX_BASE_URL"

_IST = ZoneInfo("Asia/Kolkata")

#: Intraday lookback caps imposed by Upstox's Historical Candle V3 API.
_MAX_LOOKBACK_DAYS_MINUTE = 28
_MAX_LOOKBACK_DAYS_HOURLY = 90

#: Maximum ``instrument_key`` values per Full Market Quotes request.
#:
#: Upstox's documentation permits 500 keys, but the runtime proxy in front of
#: api.upstox.com rejects a 500-key query string with HTTP 414 (Request-URI Too
#: Long) while 250 succeeds with margin.  Verified live: 500 -> 414, and
#: 250/200/150/100/50 -> 200.  This is a measured runtime limit, not a
#: documented one, so it must not be raised to 500 without re-measuring.
_MAX_QUOTE_BATCH_SIZE = 250

#: Daily OHLCV window used to derive snapshot indicators for one symbol.
#: Two years gives ~500 daily bars so EMA20/50/200 and RSI14 are all supported,
#: matching the Yahoo overlay's lookback.
_SNAPSHOT_PERIOD = "2y"

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


def _parse_retry_after(value: Any) -> float | None:
    """Parse an HTTP ``Retry-After`` header value into a non-negative float.

    Returns ``None`` when the header is absent or not a plain number, so a
    malformed value can never crash a read or be mistaken for a real delay.
    """
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed < 0:  # NaN check plus negative rejection
        return None
    return parsed


def _rate_limited_error(response: Any) -> ProviderRateLimitedError | None:
    """Build a rate-limit error for a 429 response, or ``None`` if not 429.

    Called at the only point where the response headers are still reachable.
    """
    status = getattr(response, "status_code", None)
    if status != _HTTP_TOO_MANY_REQUESTS:
        return None
    headers = getattr(response, "headers", None) or {}
    try:
        raw_retry_after = headers.get("Retry-After")
    except AttributeError:
        raw_retry_after = None
    retry_after = _parse_retry_after(raw_retry_after)
    suffix = "unspecified" if retry_after is None else f"{retry_after:g}s"
    return ProviderRateLimitedError(
        f"Upstox rate limited the request (Retry-After: {suffix})",
        retry_after=retry_after,
    )


def _default_fetch(url: str, headers: dict[str, str], timeout: float) -> Any:
    """Default HTTP GET for the Upstox Historical Candle V3 endpoint."""
    response = requests.get(url, headers=headers, timeout=timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # 429 is intercepted while the response headers are still reachable so
        # the advisory Retry-After survives.  Chaining the original HTTPError
        # keeps the existing status-based diagnostic classification intact.
        rate_limited = _rate_limited_error(response)
        if rate_limited is not None:
            raise rate_limited from exc
        raise
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
        symbol_mapper: SymbolMapper | None = None,
        fetcher: CandleFetcher | None = None,
        quote_fetcher: CandleFetcher | None = None,
        request_timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        now: Callable[[], datetime] | None = None,
        seed_provider: Any | None = None,
    ):
        self._access_token = (
            access_token if access_token is not None else _access_token_from_env()
        )
        self._base_url = (base_url or _base_url_from_env()).rstrip("/")
        self._instrument_mapper = instrument_mapper or UpstoxInstrumentMapper()
        self._symbol_mapper = symbol_mapper or SymbolMapper()
        self._fetcher = fetcher or _default_fetch
        self._quote_fetcher = quote_fetcher or _default_fetch
        self._request_timeout = request_timeout
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._seed_provider = seed_provider

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        normalized = symbol.strip().upper()
        instrument_key = self._instrument_mapper.to_instrument_key(
            self._symbol_mapper.to_listing_symbol(normalized)
        )
        unit, candle_interval = self._translate_interval(interval)
        from_date, to_date = self._translate_period(period, unit, candle_interval)
        url = self._build_url(instrument_key, unit, candle_interval, from_date, to_date)
        headers = self._build_headers()
        payload = self._fetch_json(url, headers)
        candles = self._extract_candles(payload)
        bars = [self._candle_to_bar(candle) for candle in candles]
        # Upstox returns candles oldest-first, but some responses are unordered;
        # consumers rely on ascending order, so normalize deterministically.
        bars.sort(key=lambda bar: bar.timestamp)
        logger.info(
            "fetched %d Upstox candles for %s (%s/%s)",
            len(bars),
            normalized,
            interval,
            period,
        )
        return bars

    def get_bulk_market_quotes(
        self, instrument_keys: Sequence[str]
    ) -> Sequence[MarketQuote]:
        """Fetch Full Market Quotes V3 for many instruments in bounded batches.

        The Upstox response keys each record in *colon* form (``NSE_EQ:EIEL``),
        which does not match the master's ``instrument_key``.  Records are
        therefore joined by the record's own ``instrument_token``; the response
        dictionary key is never used for identity.  Missing records are simply
        absent from the result (a live 2,656-key sweep returned 2,655) rather
        than being fabricated or raising.
        """
        keys = [str(key).strip() for key in instrument_keys if str(key).strip()]
        if not keys:
            return []
        headers = self._build_headers()
        quotes: dict[str, MarketQuote] = {}
        for start in range(0, len(keys), _MAX_QUOTE_BATCH_SIZE):
            batch = keys[start : start + _MAX_QUOTE_BATCH_SIZE]
            quotes.update(self._bulk_quotes_from_batch(batch, headers))
        logger.info(
            "fetched %d Upstox bulk quotes for %d requested instruments "
            "(batch_size=%d, batches=%d, missing=%d)",
            len(quotes),
            len(keys),
            _MAX_QUOTE_BATCH_SIZE,
            -(-len(keys) // _MAX_QUOTE_BATCH_SIZE),
            len(keys) - len(quotes),
        )
        return list(quotes.values())

    def _bulk_quotes_from_batch(
        self, batch: Sequence[str], headers: dict[str, str]
    ) -> dict[str, MarketQuote]:
        encoded = "&".join(
            f"instrument_key={quote(key, safe='')}" for key in batch
        )
        url = f"{self._base_url}/v3/market-quote/quotes?{encoded}"
        try:
            body = self._quote_fetcher(url, headers, self._request_timeout)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Upstox bulk market quote request failed for {len(batch)} "
                f"instruments: {exc}"
            ) from exc
        return self._bulk_quotes_from_payload(_as_payload(body))

    @staticmethod
    def _bulk_quotes_from_payload(payload: dict[str, Any]) -> dict[str, MarketQuote]:
        if payload.get("status") == "error":
            errors = payload.get("errors")
            message = None
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                message = errors[0].get("message")
            raise RuntimeError(
                f"Upstox bulk quote API error: {message or payload.get('message', 'unknown error')}"
            )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Upstox bulk quote response is missing the 'data' object")

        quotes: dict[str, MarketQuote] = {}
        for record in data.values():
            if not isinstance(record, dict):
                continue
            # Identity comes from instrument_token, never from the response key.
            token = record.get("instrument_token")
            if not isinstance(token, str) or not token.strip():
                continue
            quote = UpstoxMarketDataProvider._market_quote_from_record(token, record)
            if quote is not None:
                quotes[token] = quote
        return quotes

    @staticmethod
    def _market_quote_from_record(
        token: str, record: Mapping[str, Any]
    ) -> MarketQuote | None:
        def optional_number(name: str) -> float | None:
            raw = record.get(name)
            if raw is None:
                return None
            try:
                number = float(raw)
            except (TypeError, ValueError):
                return None
            return number if math.isfinite(number) else None

        price = optional_number("last_price")
        if price is None:
            logger.info("skipping Upstox bulk quote with unusable last_price token=%s", token)
            return None

        volume: int | None = None
        raw_volume = record.get("volume")
        if raw_volume is not None:
            try:
                parsed = int(float(raw_volume))
            except (TypeError, ValueError):
                parsed = -1
            if parsed >= 0:
                volume = parsed

        symbol = record.get("symbol")
        observed_at: datetime | None = None
        raw_timestamp = record.get("timestamp")
        if isinstance(raw_timestamp, str) and raw_timestamp.strip():
            try:
                observed_at = datetime.fromisoformat(raw_timestamp)
            except ValueError:
                observed_at = None

        return MarketQuote(
            instrument_key=token,
            symbol=str(symbol).strip() if isinstance(symbol, str) and symbol.strip() else token,
            price=round(price, 2),
            volume=volume,
            prev_close=optional_number("prev_close_price"),
            year_high=optional_number("year_high"),
            year_low=optional_number("year_low"),
            upper_circuit=optional_number("upper_circuit_limit"),
            lower_circuit=optional_number("lower_circuit_limit"),
            observed_at=observed_at,
        )

    def get_market_summary(self) -> dict[str, Any]:
        return self._unsupported("get_market_summary")

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        normalized = symbol.strip().upper()
        instrument_key = self._instrument_mapper.to_instrument_key(
            self._symbol_mapper.to_listing_symbol(normalized)
        )
        bars = list(
            self.get_historical_ohlcv(normalized, period=_SNAPSHOT_PERIOD, interval="1d")
        )
        if not bars:
            raise RuntimeError(f"Upstox returned no candles for {normalized}")

        if len(bars) < 2:
            raise RuntimeError(
                f"Upstox returned too few candles for {normalized} to calculate previous close"
            )
        latest, previous = bars[-1], bars[-2]
        ltp, quote_volume = self._fetch_ltp(instrument_key)
        change_pct = round(
            ((ltp - previous.close) / previous.close * 100.0) if previous.close else 0.0,
            2,
        )
        volume = (
            quote_volume
            if quote_volume is not None
            else int(latest.volume or 0)
        )

        snapshot_kwargs = self._build_live_snapshot(normalized, bars)
        payload = build_legacy_stock_from_quote(
            Instrument(
                symbol=normalized,
                name=snapshot_kwargs.pop("name"),
                sector=snapshot_kwargs.pop("sector"),
            ),
            Quote(
                symbol=normalized,
                price=ltp,
                change_pct=change_pct,
                volume=volume,
                observed_at=self._now(),
            ),
            **snapshot_kwargs,
        )
        # ADR-003: the published price is the live LTP, never a daily close.
        payload["priceSource"] = "ltp"
        return payload

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        bars = list(
            self.get_historical_ohlcv(normalized, period=_SNAPSHOT_PERIOD, interval="1d")
        )
        if not bars:
            raise RuntimeError(f"Upstox returned no candles for {normalized}")

        support, resistance, ai_insight, series = self._build_insight(normalized, bars)
        return build_legacy_insight_dict(
            StockInsight(
                symbol=normalized,
                support=support,
                resistance=resistance,
                ai_insight=ai_insight,
                series=tuple(series),
            )
        )

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
            f"UpstoxMarketDataProvider does not implement catalogue operation "
            f"{operation}; MarketDataService delegates it to the seed catalogue"
        )

    def _seed_stock_row(self, symbol: str) -> dict[str, Any] | None:
        """Return the seed catalogue row for metadata provenance (or ``None``)."""
        if self._seed_provider is None:
            return None
        row = self._seed_provider.get_stock(symbol)
        return row if isinstance(row, dict) else None

    def _fetch_ltp(self, instrument_key: str) -> tuple[float, int | None]:
        """Fetch a live LTP quote; returns ``(price, volume)``.

        The price is accepted only from the documented ``last_price`` field.
        The v2 response may key a quote by a display symbol, so the
        ``instrument_token`` inside the record is used to match the requested
        instrument key.
        """
        encoded = quote(instrument_key, safe="")
        url = f"{self._base_url}/v2/market-quote/ltp?instrument_key={encoded}"
        headers = self._build_headers()
        try:
            body = self._quote_fetcher(url, headers, self._request_timeout)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Upstox LTP quote request failed for {instrument_key}: {exc}"
            ) from exc
        payload = _as_payload(body)
        return self._ltp_from_payload(payload, instrument_key)

    @staticmethod
    def _ltp_from_payload(payload: dict[str, Any], instrument_key: str) -> tuple[float, int | None]:
        if payload.get("status") == "error":
            errors = payload.get("errors")
            message = errors[0].get("message") if isinstance(errors, list) and errors and isinstance(errors[0], dict) else payload.get("message", "unknown error")
            raise RuntimeError(f"Upstox LTP API error: {message}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Upstox LTP response is missing the 'data' object")

        quote = data.get(instrument_key)
        if not isinstance(quote, dict):
            quote = next(
                (
                    value
                    for value in data.values()
                    if isinstance(value, dict)
                    and value.get("instrument_token") == instrument_key
                ),
                None,
            )
        if not isinstance(quote, dict):
            raise RuntimeError(
                f"Upstox LTP response has no quote for {instrument_key}"
            )

        raw_price = quote.get("last_price")
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            price = float("nan")
        if not math.isfinite(price) or price <= 0:
            raise RuntimeError(
                f"Upstox LTP quote for {instrument_key} has no usable last_price field"
            )
        price = round(price, 2)

        volume: int | None = None
        raw_volume = quote.get("volume")
        if raw_volume is not None:
            try:
                parsed = int(float(raw_volume))
                if parsed >= 0:
                    volume = parsed
            except (TypeError, ValueError):
                volume = None
        return price, volume

    @staticmethod
    def _ema_if_available(values: Sequence[float], period: int) -> float | None:
        if len(values) < period:
            return None
        return round(calculate_latest_ema(values, period), 2)

    def _build_live_snapshot(
        self,
        symbol: str,
        bars: Sequence[OHLCVBar],
    ) -> dict[str, Any]:
        seed = self._seed_stock_row(symbol)
        closes = [bar.close for bar in bars if math.isfinite(bar.close)]
        highs = [bar.high for bar in bars if math.isfinite(bar.high)]
        lows = [bar.low for bar in bars if math.isfinite(bar.low)]
        volumes = [bar.volume or 0.0 for bar in bars]

        if len(closes) < 20:
            raise RuntimeError(
                f"Upstox returned too few daily candles for {symbol} to compute indicators"
            )
        rsi = round(calculate_latest_rsi(closes, 14), 2)
        ema20 = self._ema_if_available(closes, 20)
        if ema20 is None:
            raise RuntimeError(f"Upstox cannot compute EMA20 for {symbol}")
        ema50 = self._ema_if_available(closes, 50)
        ema200 = self._ema_if_available(closes, 200)
        vwap = round(
            calculate_rolling_vwap(
                highs=highs,
                lows=lows,
                closes=closes,
                volumes=volumes,
                period=20,
            ),
            2,
        )

        recent = bars[-20:]
        support = round(min(bar.low for bar in recent), 2)
        resistance = round(max(bar.high for bar in recent), 2)
        computed_day_high = round(max(bar.high for bar in recent), 2)
        positive_volumes = [int(v) for v in volumes if v and v > 0]
        computed_avg_volume = (
            int(sum(positive_volumes) / len(positive_volumes))
            if positive_volumes
            else 0
        )

        if seed is not None:
            name, sector = seed.get("name", symbol), seed.get("sector", "Equities")
            trend, score = seed.get("trend", "neutral"), seed.get("score")
            day_high = float(seed.get("day_high", computed_day_high))
            avg_volume = int(seed.get("avg_volume", computed_avg_volume))
        else:
            name, sector = symbol, "Equities"
            trend, score = "neutral", None
            day_high, avg_volume = computed_day_high, computed_avg_volume

        return {
            "name": name,
            "sector": sector,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "vwap": vwap,
            "trend": trend,
            "score": score,
            "support": support,
            "resistance": resistance,
            "day_high": day_high,
            "avg_volume": avg_volume,
        }

    def _build_insight(
        self,
        symbol: str,
        bars: Sequence[OHLCVBar],
    ) -> tuple[float, float, str, list[dict[str, Any]]]:
        """Derive support/resistance, an indicator sentence, and a mini series."""
        recent = bars[-20:]
        support = round(min(bar.low for bar in recent), 2)
        resistance = round(max(bar.high for bar in recent), 2)
        closes = [bar.close for bar in bars if math.isfinite(bar.close)]
        price = closes[-1] if closes else 0.0
        ema20 = self._ema_if_available(closes, 20) or price
        bias = "above" if price >= ema20 else "below"
        ai_insight = (
            f"Price {price:.2f} is {bias} EMA20 {ema20:.2f}; "
            f"support {support:.2f} and resistance {resistance:.2f}."
        )
        series = [
            {
                "t": bar.timestamp.strftime("%Y-%m-%d"),
                "v": round(bar.close, 2),
            }
            for bar in bars[-13:]
        ]
        logger.info("built Upstox insight series=%d symbol=%s", len(series), symbol)
        return support, resistance, ai_insight, series

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

    def _translate_period(
        self,
        period: str,
        unit: str,
        candle_interval: str,
    ) -> tuple[date, date]:
        """Translate periods to absolute dates, in IST, respecting V3 caps.

        ``to_date`` is always today in India's timezone (``n/a`` otherwise the
        API rejects a future/exchange-relative date).  Upstox's V3 lookback
        limits are enforced for intraday candles regardless of the requested
        ``period``: 1-15 minute candles go back at most 28 days, and 30+ minute
        or hourly candles at most 90 days.  Daily/weekly/monthly requests keep
        the full translated window.
        """
        to_date = self._now().astimezone(_IST).date()
        try:
            minutes = int(candle_interval)
        except (TypeError, ValueError):
            minutes = 0
        if unit == "minutes" and 0 < minutes <= 15:
            from_date = to_date - timedelta(days=_MAX_LOOKBACK_DAYS_MINUTE)
            return from_date, to_date
        if unit == "minutes" or unit == "hours":
            from_date = to_date - timedelta(days=_MAX_LOOKBACK_DAYS_HOURLY)
            return from_date, to_date

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
        except ProviderRateLimitedError:
            # Carries the parsed Retry-After; must not be flattened into a
            # plain RuntimeError or the pacing signal is lost.
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            # A custom/injected fetcher may raise HTTPError directly instead of
            # routing through _default_fetch, so normalize a 429 here too.
            rate_limited = _rate_limited_error(getattr(exc, "response", None))
            if rate_limited is not None:
                raise rate_limited from exc
            raise RuntimeError(
                f"Upstox historical candle request failed for {url}: {exc}"
            ) from exc
        rate_limited = _rate_limited_error(body)
        if rate_limited is not None:
            raise rate_limited
        return _as_payload(body)

    @staticmethod
    def _extract_candles(payload: dict[str, Any]) -> list[Any]:
        if payload.get("status") == "error":
            message = None
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0]
                if isinstance(first, dict):
                    message = first.get("message")
            if not message:
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

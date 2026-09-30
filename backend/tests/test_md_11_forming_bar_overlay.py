"""MD-11: forming-bar overlay onto today's in-progress daily bar.

During the OPEN session the daily OHLCV series consumed by Stage-2 screening
ends with a *forming bar* whose close is a stale first print.  This overlays the
live quote that MD-10 bulk discovery already fetched, so RSI/EMA see the live
close.

Product note: daily indicators therefore move while the market is OPEN.  That
is intentional; no smoothing or freezing is applied.

The overlay reuses ``MarketQuote`` from the canonical MD-10 path.  No
``LiveSnapshot`` type, no second provider bulk method, and no extra provider
call is involved: the Stage-1 quotes are carried into Stage-2.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from services import market_scanner as scanner_module
from services.market_data.indicators import calculate_latest_rsi
from services.market_data.models import MarketQuote, OHLCVBar
from services.market_scanner import MarketScanner, ScannerConfig, overlay_forming_bar

_IST = ZoneInfo("Asia/Kolkata")


def _bar(day_offset: int, close: float) -> OHLCVBar:
    """A daily bar stamped at IST midnight ``day_offset`` days from 2026-01-01."""
    day = date(2026, 1, 1) + timedelta(days=day_offset)
    return OHLCVBar(
        timestamp=datetime(day.year, day.month, day.day, tzinfo=_IST),
        open=close - 1.0,
        high=close + 1.0,
        low=close - 2.0,
        close=close,
        volume=1_000.0,
    )


def _ohlcv_bars(count: int = 60, end_offset: int = 0) -> tuple[OHLCVBar, ...]:
    return tuple(_bar(index - (count + end_offset), 100.0 + index) for index in range(count))


def _today() -> date:
    return datetime.now(_IST).date()


def _quote(price: float = 120.0, volume: int | None = 42) -> MarketQuote:
    return MarketQuote(
        instrument_key="NSE_EQ|RELIANCE-EQ",
        symbol="RELIANCE",
        price=price,
        volume=volume,
        prev_close=100.0,
    )


# ---------------------------------------------------------------------------
# Pure forming-bar overlay
# ---------------------------------------------------------------------------


def test_overlay_applies_only_to_today_forming_bar() -> None:
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()

    overlaid = overlay_forming_bar(bars, _quote(price=120.0, volume=42), today)

    assert isinstance(overlaid, tuple)
    assert len(overlaid) == len(bars)
    for original, result in zip(bars[:-1], overlaid[:-1]):
        assert result is original  # completed bars returned untouched
    assert overlaid[-1].close == 120.0
    assert overlaid[-1].volume == 42.0
    assert overlaid[-1].timestamp == bars[-1].timestamp
    assert overlaid[-1].open == bars[-1].open


def test_overlay_keeps_previous_close_unchanged() -> None:
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()

    overlaid = overlay_forming_bar(bars, _quote(price=120.0), today)

    assert overlaid[-2].close == bars[-2].close


def test_overlay_preserves_bar_when_quote_has_no_volume() -> None:
    """Volume is optional on ``MarketQuote``; the historical value must survive."""
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()

    overlaid = overlay_forming_bar(bars, _quote(price=120.0, volume=None), today)

    assert overlaid[-1].volume == bars[-1].volume


def test_overlay_keeps_bar_internally_consistent_on_a_large_move() -> None:
    """A live price above the day's high must not produce ``high < close``.

    ``MarketQuote`` has no intraday high/low, so the overlay widens the
    existing range instead of trusting a stale one.
    """
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()
    latest = bars[-1]

    overlaid = overlay_forming_bar(bars, _quote(price=latest.high + 50.0), today)

    assert overlaid[-1].high == latest.high + 50.0
    assert overlaid[-1].low <= overlaid[-1].close <= overlaid[-1].high


def test_overlay_low_is_not_raised_above_a_dive() -> None:
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()
    latest = bars[-1]

    overlaid = overlay_forming_bar(bars, _quote(price=latest.low - 10.0), today)

    assert overlaid[-1].low == latest.low - 10.0
    assert overlaid[-1].low <= overlaid[-1].close <= overlaid[-1].high


def test_overlay_noops_when_forming_bar_is_not_today() -> None:
    bars = _ohlcv_bars(end_offset=-1)  # last bar is yesterday

    overlaid = overlay_forming_bar(bars, _quote(price=120.0), _today())

    assert overlaid is bars


def test_overlay_noops_without_quote() -> None:
    bars = _ohlcv_bars()

    assert overlay_forming_bar(bars, None, _today()) is bars


def test_overlay_noops_with_empty_bars() -> None:
    assert overlay_forming_bar((), _quote(price=120.0), _today()) == ()


def test_overlay_noops_for_non_positive_price() -> None:
    bars = _ohlcv_bars()
    today = bars[-1].timestamp.astimezone(_IST).date()

    assert overlay_forming_bar(bars, _quote(price=0.0), today) is bars


def test_overlay_ignores_a_bar_stamped_in_utc_for_the_same_instant() -> None:
    """A tz-aware timestamp must be compared in IST, not by raw ``.date()``."""
    ist_day = date(2026, 3, 10)
    bar = OHLCVBar(
        # 18:30 UTC on 2026-03-09 == 00:00 IST on 2026-03-10.
        timestamp=datetime(2026, 3, 9, 18, 30, tzinfo=timezone.utc),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=10.0,
    )

    overlaid = overlay_forming_bar((bar,), _quote(price=120.0), ist_day)

    assert overlaid[-1].close == 120.0


def test_overlaid_bar_is_usable_by_rsi() -> None:
    """Acceptance: the result must stay suitable for downstream RSI."""
    # An oscillating series keeps RSI off its 0/100 rails, so the assertion that
    # the live close actually moves the indicator is meaningful.
    bars = tuple(
        _bar(index - 60, 100.0 + (4.0 if index % 2 else 0.0)) for index in range(60)
    )
    today = bars[-1].timestamp.astimezone(_IST).date()
    before = calculate_latest_rsi([bar.close for bar in bars], 14)
    assert 0.0 < before < 100.0, "fixture must not saturate RSI"

    overlaid = overlay_forming_bar(bars, _quote(price=140.0), today)
    after = calculate_latest_rsi([bar.close for bar in overlaid], 14)

    assert 0.0 <= after <= 100.0
    assert after != before, "the live close must reach the indicator"


# ---------------------------------------------------------------------------
# Scanner-level session / attribution gates
# ---------------------------------------------------------------------------


class _FakeService:
    """Minimal ``MarketDataService`` stand-in exposing the scanner's two calls."""

    supports_bulk_market_quotes = True

    def __init__(
        self,
        bars: tuple[OHLCVBar, ...],
        quote_provider: str = "upstox",
        quote: float = 500.0,
    ) -> None:
        self._bars = bars
        self._quote_provider = quote_provider
        self._quote_price = quote
        self.historical_calls: list[str] = []
        self.bulk_calls: list[int] = []

    def get_historical_ohlcv(self, symbol: str, *, period: str, interval: str):
        self.historical_calls.append(symbol)
        provider = "seed" if symbol.endswith("B") else self._quote_provider
        return SimpleNamespace(
            data=self._bars, metadata=SimpleNamespace(provider=provider)
        )

    def get_bulk_market_quotes(self, instrument_keys):
        self.bulk_calls.append(len(instrument_keys))
        return SimpleNamespace(
            data=tuple(
                MarketQuote(
                    instrument_key=key,
                    symbol=key.split("|")[-1],
                    price=self._quote_price,
                    volume=1_000_000,
                    prev_close=100.0,
                    year_high=self._quote_price * 1.01,
                    year_low=self._quote_price * 0.6,
                )
                for key in instrument_keys
            ),
            metadata=SimpleNamespace(provider=self._quote_provider),
        )


def _scanner(service, **config) -> MarketScanner:
    return MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={"RELIANCE": "NSE_EQ|RELIANCE-EQ"},
        config=ScannerConfig(**config),
    )


def _force_session(monkeypatch, status: str) -> None:
    monkeypatch.setattr(scanner_module, "market_session_status", lambda now=None: status)


def _prefilter_with_quote(service) -> "MarketScanner._PrefilterOutcome":
    """Build the outcome ``_resolve_stage_two_targets`` would return."""
    return MarketScanner._PrefilterOutcome(
        applied=True,
        quotes_by_key={"NSE_EQ|RELIANCE-EQ": _quote(price=500.0)},
        quote_provider=service._quote_provider,
    )


def test_scanner_overlays_forming_bar_during_open(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")
    bars_today = (
        *bars[:-1],
        OHLCVBar(
            timestamp=datetime.combine(
                datetime.now(_IST).date(), datetime.min.time(), tzinfo=_IST
            ),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1_000.0,
        ),
    )
    service._bars = bars_today

    prefilter = _prefilter_with_quote(service)
    applied = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars_today, "upstox", prefilter
    )

    assert applied[-1].close == 500.0


def test_scanner_no_overlay_when_session_closed(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "CLOSED")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert result == bars


def test_scanner_no_overlay_during_pre_open(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "PRE_OPEN")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert result == bars


def test_scanner_no_overlay_on_weekend(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "WEEKEND")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert result == bars


def test_scanner_no_overlay_for_intraday_interval(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service, interval="5m")
    _force_session(monkeypatch, "OPEN")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert result == bars


def test_scanner_no_overlay_when_providers_differ(monkeypatch) -> None:
    """Attribution gate: a Yahoo historical bar must not take an Upstox quote."""
    bars = _ohlcv_bars()
    service = _FakeService(bars, quote_provider="upstox")
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "yahoo", _prefilter_with_quote(service)
    )

    assert result == bars


def test_scanner_no_overlay_without_prefilter(monkeypatch) -> None:
    """The non-bulk fallback path has no quotes, so historical data is untouched."""
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", None
    )

    assert result == bars


def test_scanner_no_overlay_when_quote_missing_for_symbol(monkeypatch) -> None:
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")
    prefilter = MarketScanner._PrefilterOutcome(
        applied=True,
        quotes_by_key={"NSE_EQ|OTHER-EQ": _quote(price=500.0)},
        quote_provider="upstox",
    )

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", prefilter
    )

    assert result == bars


def test_scanner_overlay_adds_no_provider_call(monkeypatch) -> None:
    """The overlay must reuse Stage-1's fetch, never issue its own."""
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")

    scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert service.bulk_calls == []
    assert service.historical_calls == []


def test_full_scan_overlays_and_adds_no_extra_bulk_call(monkeypatch) -> None:
    """End-to-end through ``scan()``: exactly one bulk call, as before MD-11."""
    bars = _ohlcv_bars()
    bars_today = (
        *bars[:-1],
        OHLCVBar(
            timestamp=datetime.combine(
                datetime.now(_IST).date(), datetime.min.time(), tzinfo=_IST
            ),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1_000.0,
        ),
    )
    service = _FakeService(bars_today, quote=500.0)
    scanner = _scanner(service)
    _force_session(monkeypatch, "OPEN")

    screened: list[tuple[OHLCVBar, ...]] = []
    original = scanner._screen

    def _capture(instrument, bars_in, provider):
        screened.append(bars_in)
        return original(instrument, bars_in, provider)

    monkeypatch.setattr(scanner, "_screen", _capture)
    result = scanner.scan()

    assert result.metrics.bulk_prefilter_applied is True
    assert service.bulk_calls == [1], "overlay must reuse the Stage-1 fetch"
    assert service.historical_calls == ["RELIANCE"]
    # The bar that reached the indicators carried the live close.
    assert screened[0][-1].close == 500.0
    assert screened[0][-2].close == bars_today[-2].close


@pytest.mark.parametrize("status", ["CLOSED", "PRE_OPEN", "WEEKEND"])
def test_session_gate_is_exclusive_of_open(monkeypatch, status: str) -> None:
    """Boundary: only OPEN may overlay; every neighbouring bucket must not."""
    bars = _ohlcv_bars()
    service = _FakeService(bars)
    scanner = _scanner(service)
    _force_session(monkeypatch, status)

    result = scanner._apply_forming_bar_overlay(
        scanner._instruments[0], bars, "upstox", _prefilter_with_quote(service)
    )

    assert result is bars

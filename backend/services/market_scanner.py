"""Fast, provider-neutral screening over the validated NSE equity universe."""
from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from statistics import mean
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from services.market_data.broad_market_prefilter import (
    DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES,
    DEFAULT_YEAR_HIGH_PROXIMITY_PCT,
    apply_stage_one_gates,
    select_stage_two_candidates,
)
from services.market_data.indicators import calculate_latest_ema, calculate_latest_rsi
from services.market_data.models import MarketQuote, OHLCVBar
from services.market_data.session import market_session_status
from services.market_data_service import MarketDataService
from services.providers.upstox_instrument_source import load_instrument_master

logger = logging.getLogger("tradelens.market_scanner")

_IST = ZoneInfo("Asia/Kolkata")


def overlay_forming_bar(
    bars: Sequence[OHLCVBar],
    quote: MarketQuote | None,
    today: date,
) -> Sequence[OHLCVBar]:
    """Overlay a live quote onto today's forming daily bar.

    Only the *last* bar is considered, and only when it belongs to the supplied
    ``today`` IST trading date; historical bars are never touched and a quote
    for a day that is not represented as the forming bar is ignored.  The input
    sequence is returned unchanged when no overlay applies.

    A ``MarketQuote`` carries no intraday high/low, so today's high/low are
    widened to include the live price.  This keeps ``low <= close <= high``
    (and therefore the bar usable by RSI/EMA) even when the provider's daily
    candle has not yet absorbed a large move.  ``open`` and every completed bar
    are preserved: the live quote is not authoritative for them.
    """
    if quote is None or not bars:
        return bars
    latest = bars[-1]
    if latest.timestamp.astimezone(_IST).date() != today:
        return bars
    close = quote.price
    if not math.isfinite(close) or close <= 0:
        return bars
    volume = float(quote.volume) if quote.volume is not None else latest.volume
    overlaid = OHLCVBar(
        timestamp=latest.timestamp,
        open=latest.open,
        high=max(latest.high, close),
        low=min(latest.low, close),
        close=round(close, 2),
        volume=volume,
    )
    return (*bars[:-1], overlaid)


@dataclass(frozen=True)
class ScannerConfig:
    """Small, transparent first-pass screening configuration."""

    period: str = "1y"
    interval: str = "1d"
    minimum_bars: int = 50
    minimum_average_volume: float = 100_000.0
    momentum_lookback: int = 10
    structure_lookback: int = 20
    maximum_daily_move_pct: float = 15.0
    minimum_momentum_rsi: float = 50.0
    maximum_momentum_rsi: float = 80.0
    #: Stage-1 bulk prefilter (MD-10).  These only narrow *which* instruments
    #: get a historical fetch; they never change technical screening.
    bulk_prefilter_enabled: bool = True
    year_high_proximity_pct: float = DEFAULT_YEAR_HIGH_PROXIMITY_PCT
    maximum_stage_two_candidates: int = DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES
    historical_fetch_concurrency: int = 16


@dataclass(frozen=True)
class ScannerFunnelMetrics:
    universe_count: int = 0
    data_available_count: int = 0
    liquidity_pass_count: int = 0
    trend_pass_count: int = 0
    momentum_pass_count: int = 0
    technical_pass_count: int = 0
    final_candidate_count: int = 0
    #: Stage-1 / Stage-2 funnel (MD-10).  ``historical_candidate_count`` are
    #: inputs to technical screening, *not* technical candidates.
    bulk_snapshot_requested: int = 0
    bulk_snapshot_returned: int = 0
    stage_one_eligible_count: int = 0
    stage_two_selected_count: int = 0
    stage_two_cap: int = 0
    bulk_prefilter_applied: bool = False
    bulk_prefilter_fallback_reason: str | None = None

    @property
    def eligible_count(self) -> int:
        """Universe instruments eligible to be attempted by this scan."""
        if self.bulk_prefilter_applied:
            return self.stage_two_selected_count
        return self.universe_count

    @property
    def scanned_count(self) -> int:
        """Instruments for which usable historical data was obtained."""
        return self.data_available_count

    @property
    def candidate_count(self) -> int:
        return self.final_candidate_count

@dataclass(frozen=True)
class ScreeningResult:
    symbol: str
    instrument_key: str
    passed: bool
    score: int
    signals: Mapping[str, bool]
    reason_codes: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    provider: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ScanResult:
    results: tuple[ScreeningResult, ...]
    metrics: ScannerFunnelMetrics

    @property
    def candidates(self) -> tuple[ScreeningResult, ...]:
        return tuple(result for result in self.results if result.passed)

    @property
    def rejected_by_reason(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            for reason in result.rejection_reasons:
                counts[reason] = counts.get(reason, 0) + 1
        return counts


@dataclass(frozen=True)
class _Instrument:
    symbol: str
    instrument_key: str


class MarketScanner:
    """Apply cheap deterministic filters before later deep analysis."""

    def __init__(
        self,
        market_data_service: MarketDataService,
        *,
        instrument_mapping: Mapping[str, str] | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        self._market_data_service = market_data_service
        self._config = config or ScannerConfig()
        mapping = instrument_mapping or load_instrument_master()
        self._instruments = tuple(
            _Instrument(symbol=symbol.strip().upper(), instrument_key=key)
            for symbol, key in sorted(mapping.items())
        )

    @property
    def universe_symbols(self) -> tuple[str, ...]:
        return tuple(instrument.symbol for instrument in self._instruments)

    def scan(self) -> ScanResult:
        """Scan the master universe, isolating failures to one symbol.

        Broad-market runs (MD-10) are two-stage: one bulk live-quote snapshot
        prefilters the universe down to a bounded set of historical-screening
        inputs, which are then fetched with bounded concurrency.  When the active
        provider has no bulk capability the full universe is still scanned, so
        non-Upstox providers behave exactly as before.
        """
        targets, prefilter = self._resolve_stage_two_targets()

        results: list[ScreeningResult] = []
        data_available = liquidity = trend = momentum = technical = candidates = 0

        for result in self._screen_instruments(targets, prefilter):
            results.append(result)
            if result.rejection_reasons != ("data_unavailable",):
                data_available += 1
            liquidity_passed = result.signals.get("liquidity", False)
            trend_passed = liquidity_passed and result.signals.get("trend", False)
            momentum_passed = trend_passed and result.signals.get("momentum", False)
            technical_passed = momentum_passed and result.signals.get("technical", False)
            if liquidity_passed:
                liquidity += 1
            if trend_passed:
                trend += 1
            if momentum_passed:
                momentum += 1
            if technical_passed:
                technical += 1
            if result.passed:
                candidates += 1

        metrics = ScannerFunnelMetrics(
            universe_count=len(self._instruments),
            data_available_count=data_available,
            liquidity_pass_count=liquidity,
            trend_pass_count=trend,
            momentum_pass_count=momentum,
            technical_pass_count=technical,
            final_candidate_count=candidates,
            bulk_snapshot_requested=prefilter.snapshot_requested,
            bulk_snapshot_returned=prefilter.snapshot_returned,
            stage_one_eligible_count=prefilter.eligible_count,
            stage_two_selected_count=prefilter.selected_count,
            stage_two_cap=prefilter.cap,
            bulk_prefilter_applied=prefilter.applied,
            bulk_prefilter_fallback_reason=prefilter.fallback_reason,
        )
        logger.info(
            "market_scanner.completed universe=%d attempted=%d data=%d candidates=%d "
            "prefilter_applied=%s stage_two_selected=%d stage_two_cap=%d",
            metrics.universe_count,
            len(results),
            metrics.data_available_count,
            metrics.final_candidate_count,
            metrics.bulk_prefilter_applied,
            metrics.stage_two_selected_count,
            metrics.stage_two_cap,
        )
        return ScanResult(results=tuple(results), metrics=metrics)

    @dataclass(frozen=True)
    class _PrefilterOutcome:
        """Stage-1/Stage-2 funnel diagnostics for one scan."""

        applied: bool = False
        fallback_reason: str | None = None
        snapshot_requested: int = 0
        snapshot_returned: int = 0
        eligible_count: int = 0
        selected_count: int = 0
        cap: int = 0
        #: Live quotes keyed by instrument key, carried from the Stage-1 bulk
        #: call so the forming-bar overlay reuses that single fetch instead of
        #: issuing one more request per symbol.
        quotes_by_key: Mapping[str, MarketQuote] = field(default_factory=dict)
        #: Provider attribution of the Stage-1 bulk call.  The overlay only
        #: applies when this matches the historical read's provider.
        quote_provider: str | None = None

    def _resolve_stage_two_targets(
        self,
    ) -> tuple[tuple[_Instrument, ...], MarketScanner._PrefilterOutcome]:
        """Apply the Stage-1 prefilter and return Stage-2 historical targets.

        Any failure of the optional bulk path (provider without the capability,
        a transport error, or a short snapshot that cannot safely narrow the
        universe) falls back to the full universe, which is exactly the previous
        behavior.  Fallbacks are explicit in diagnostics so a run is never
        silently reported as prefiltered.
        """
        full_universe = self._instruments
        if not self._config.bulk_prefilter_enabled:
            return full_universe, self._PrefilterOutcome(
                fallback_reason="bulk_prefilter_disabled"
            )

        instrument_keys = [instrument.instrument_key for instrument in self._instruments]
        if not getattr(self._market_data_service, "supports_bulk_market_quotes", False):
            logger.info(
                "market_scanner.bulk_prefilter_unavailable provider=%s",
                type(self._market_data_service).__name__,
            )
            return full_universe, self._PrefilterOutcome(
                fallback_reason="provider_unsupported"
            )

        try:
            market_data = self._market_data_service.get_bulk_market_quotes(
                instrument_keys
            )
        except NotImplementedError:
            logger.info(
                "market_scanner.bulk_prefilter_unavailable provider=%s",
                getattr(self._market_data_service, "name", "unknown"),
            )
            return full_universe, self._PrefilterOutcome(
                fallback_reason="provider_unsupported"
            )
        except Exception as exc:
            logger.warning(
                "market_scanner.bulk_prefilter_failed symbols=%d",
                len(instrument_keys),
                exc_info=True,
            )
            return full_universe, self._PrefilterOutcome(
                fallback_reason=f"bulk_snapshot_error:{type(exc).__name__}"
            )

        quotes = tuple(market_data.data)
        if not quotes:
            logger.warning(
                "market_scanner.bulk_prefilter_empty symbols=%d", len(instrument_keys)
            )
            return full_universe, self._PrefilterOutcome(
                snapshot_requested=len(instrument_keys),
                fallback_reason="empty_bulk_snapshot",
            )

        stage_one = apply_stage_one_gates(
            quotes,
            year_high_proximity_pct=self._config.year_high_proximity_pct,
        )
        selection = select_stage_two_candidates(
            stage_one,
            cap=self._config.maximum_stage_two_candidates,
        )
        if not selection.selected:
            logger.warning(
                "market_scanner.bulk_prefilter_no_candidates returned=%d proximity_pct=%.1f",
                stage_one.snapshot_returned,
                self._config.year_high_proximity_pct,
            )
            return full_universe, self._PrefilterOutcome(
                snapshot_requested=len(instrument_keys),
                snapshot_returned=stage_one.snapshot_returned,
                eligible_count=stage_one.eligible_count,
                cap=selection.cap,
                fallback_reason="no_stage_one_candidates",
            )

        by_key = {instrument.instrument_key: instrument for instrument in self._instruments}
        # Join on the normalized master key.  A snapshot key with no universe
        # entry is dropped rather than screened against nothing.
        targets = tuple(
            by_key[quote.instrument_key]
            for quote in selection.selected
            if quote.instrument_key in by_key
        )
        logger.info(
            "market_scanner.bulk_prefilter_applied universe=%d returned=%d "
            "stage_one_eligible=%d stage_two_selected=%d cap=%d proximity_pct=%.1f",
            len(self._instruments),
            stage_one.snapshot_returned,
            stage_one.eligible_count,
            len(targets),
            selection.cap,
            self._config.year_high_proximity_pct,
        )
        return targets, self._PrefilterOutcome(
            applied=True,
            snapshot_requested=len(instrument_keys),
            snapshot_returned=stage_one.snapshot_returned,
            eligible_count=stage_one.eligible_count,
            selected_count=len(targets),
            cap=selection.cap,
            quotes_by_key={
                quote.instrument_key: quote for quote in selection.selected
            },
            quote_provider=market_data.metadata.provider,
        )

    def _screen_instruments(
        self,
        targets: tuple[_Instrument, ...],
        prefilter: MarketScanner._PrefilterOutcome | None = None,
    ) -> tuple[ScreeningResult, ...]:
        """Fetch and screen Stage-2 targets with bounded concurrency.

        Concurrency changes only *when* historical data is fetched, never what
        is computed: each target goes through the identical ``_screen()`` path
        and a per-symbol failure is still isolated to that one symbol.  Results
        keep the input order so a scan is deterministic.
        """
        if not targets:
            return ()
        max_workers = max(1, min(self._config.historical_fetch_concurrency, len(targets)))
        if max_workers == 1:
            return tuple(
                self._screen_one(instrument, prefilter) for instrument in targets
            )
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="market_scanner"
        ) as executor:
            return tuple(
                executor.map(
                    lambda instrument: self._screen_one(instrument, prefilter),
                    targets,
                )
            )

    def _screen_one(
        self,
        instrument: _Instrument,
        prefilter: MarketScanner._PrefilterOutcome | None = None,
    ) -> ScreeningResult:
        try:
            market_data = self._market_data_service.get_historical_ohlcv(
                instrument.symbol,
                period=self._config.period,
                interval=self._config.interval,
            )
            bars = tuple(market_data.data)
            if not bars:
                raise ValueError("empty historical OHLCV")
            provider = market_data.metadata.provider
            bars = self._apply_forming_bar_overlay(
                instrument, bars, provider, prefilter
            )
            return self._screen(instrument, bars, provider)
        except Exception as exc:
            logger.warning(
                "market_scanner.symbol_failed symbol=%s",
                instrument.symbol,
                exc_info=True,
            )
            return ScreeningResult(
                symbol=instrument.symbol,
                instrument_key=instrument.instrument_key,
                passed=False,
                score=0,
                signals={},
                rejection_reasons=("data_unavailable",),
                error=str(exc),
            )

    def _apply_forming_bar_overlay(
        self,
        instrument: _Instrument,
        bars: tuple[OHLCVBar, ...],
        provider: str,
        prefilter: MarketScanner._PrefilterOutcome | None,
    ) -> tuple[OHLCVBar, ...]:
        """Overlay today's live quote onto today's forming daily bar (MD-11).

        Reuses the Stage-1 MD-10 bulk fetch, so this adds no provider call.  The
        overlay is skipped unless every gate holds:

        * the session is OPEN, so a completed bar is never rewritten;
        * the interval is daily, so intraday series are untouched;
        * the Stage-1 quote was served by the same provider that served the
          historical bars, so a cross-provider quote is never mixed in.

        While the market is OPEN this deliberately makes daily indicators
        (RSI/EMA) move with the live close.  That is intended, not smoothed
        away: the forming bar is the most recent information available.
        """
        if prefilter is None or not prefilter.quotes_by_key:
            return bars
        if self._config.interval.strip().lower() != "1d":
            return bars
        now = datetime.now(timezone.utc)
        if market_session_status(now) != "OPEN":
            return bars
        if prefilter.quote_provider != provider:
            logger.info(
                "market_scanner.forming_bar_overlay_skipped symbol=%s reason=provider_mismatch "
                "quote_provider=%s historical_provider=%s",
                instrument.symbol,
                prefilter.quote_provider,
                provider,
            )
            return bars
        quote = prefilter.quotes_by_key.get(instrument.instrument_key)
        if quote is None:
            return bars
        overlaid = overlay_forming_bar(bars, quote, now.astimezone(_IST).date())
        if len(overlaid) == len(bars) and overlaid[-1] is bars[-1]:
            return bars
        logger.info(
            "market_scanner.forming_bar_overlay_applied symbol=%s close=%s->%s",
            instrument.symbol,
            bars[-1].close,
            overlaid[-1].close,
        )
        return tuple(overlaid)

    def _screen(
        self,
        instrument: _Instrument,
        bars: tuple[OHLCVBar, ...],
        provider: str,
    ) -> ScreeningResult:
        config = self._config
        if len(bars) < config.minimum_bars:
            return ScreeningResult(
                symbol=instrument.symbol,
                instrument_key=instrument.instrument_key,
                passed=False,
                score=0,
                signals={},
                rejection_reasons=("insufficient_history",),
                provider=provider,
            )

        closes = [bar.close for bar in bars]
        volumes = [bar.volume or 0.0 for bar in bars]
        recent = bars[-config.structure_lookback :]
        average_volume = mean(volumes[-config.structure_lookback :])
        ema20 = calculate_latest_ema(closes, 20)
        ema50 = calculate_latest_ema(closes, 50)
        rsi = calculate_latest_rsi(closes, 14)
        latest = bars[-1]
        previous_close = closes[-config.momentum_lookback - 1]
        momentum_pct = (latest.close / previous_close - 1.0) * 100.0
        support = min(bar.low for bar in recent)
        resistance = max(bar.high for bar in recent)
        prior_resistance = max(bar.high for bar in bars[-config.structure_lookback - 1 : -1])
        prior_support = min(bar.low for bar in bars[-config.structure_lookback - 1 : -1])
        recent_moves = [
            abs((current.close / previous.close - 1.0) * 100.0)
            for previous, current in zip(bars[-21:-1], bars[-20:])
            if previous.close > 0
        ]

        signals = {
            "liquidity": (
                latest.volume is not None
                and latest.volume >= config.minimum_average_volume
                and average_volume >= config.minimum_average_volume
            ),
            "trend": latest.close > ema20 > ema50,
            "momentum": (
                config.minimum_momentum_rsi <= rsi <= config.maximum_momentum_rsi
                and momentum_pct > 0.0
            ),
            "support_resistance": (
                latest.close >= resistance * 0.98
                or latest.close <= support * 1.02
            ),
            "breakout_breakdown": (
                latest.close >= prior_resistance or latest.close <= prior_support
            ),
            "volatility": bool(recent_moves)
            and max(recent_moves) <= config.maximum_daily_move_pct,
        }
        signals["technical"] = (
            (signals["support_resistance"] or signals["breakout_breakdown"])
            and signals["volatility"]
        )
        stages = ("liquidity", "trend", "momentum", "technical")
        reasons = tuple(f"failed_{stage}" for stage in stages if not signals[stage])
        qualifying = tuple(
            f"{signal}_signal"
            for signal, passed in signals.items()
            if passed and signal != "technical"
        )
        score = sum(20 for key in stages if signals[key])
        passed = not reasons
        return ScreeningResult(
            symbol=instrument.symbol,
            instrument_key=instrument.instrument_key,
            passed=passed,
            score=score,
            signals=signals,
            reason_codes=qualifying,
            rejection_reasons=reasons,
            provider=provider,
        )

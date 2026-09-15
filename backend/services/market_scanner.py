"""Fast, provider-neutral screening over the validated NSE equity universe."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Mapping

from services.market_data.indicators import calculate_latest_ema, calculate_latest_rsi
from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService
from services.providers.upstox_instrument_source import load_instrument_master

logger = logging.getLogger("tradelens.market_scanner")


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


@dataclass(frozen=True)
class ScannerFunnelMetrics:
    universe_count: int = 0
    data_available_count: int = 0
    liquidity_pass_count: int = 0
    trend_pass_count: int = 0
    momentum_pass_count: int = 0
    technical_pass_count: int = 0
    final_candidate_count: int = 0

    @property
    def eligible_count(self) -> int:
        """Universe instruments eligible to be attempted by this scan."""
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
        """Scan every master instrument, isolating failures to one symbol."""
        results: list[ScreeningResult] = []
        data_available = liquidity = trend = momentum = technical = candidates = 0

        for instrument in self._instruments:
            try:
                market_data = self._market_data_service.get_historical_ohlcv(
                    instrument.symbol,
                    period=self._config.period,
                    interval=self._config.interval,
                )
                bars = tuple(market_data.data)
                if not bars:
                    raise ValueError("empty historical OHLCV")
                data_available += 1
                result = self._screen(instrument, bars, market_data.metadata.provider)
            except Exception as exc:
                logger.warning(
                    "market_scanner.symbol_failed symbol=%s",
                    instrument.symbol,
                    exc_info=True,
                )
                result = ScreeningResult(
                    symbol=instrument.symbol,
                    instrument_key=instrument.instrument_key,
                    passed=False,
                    score=0,
                    signals={},
                    rejection_reasons=("data_unavailable",),
                    error=str(exc),
                )

            results.append(result)
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
        )
        logger.info(
            "market_scanner.completed universe=%d data=%d candidates=%d",
            metrics.universe_count,
            metrics.data_available_count,
            metrics.final_candidate_count,
        )
        return ScanResult(results=tuple(results), metrics=metrics)

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

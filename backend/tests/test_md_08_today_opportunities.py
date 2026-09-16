"""Deterministic MD-08 Today's Opportunities integration tests."""
from __future__ import annotations

from types import SimpleNamespace
import time

from services.deep_analysis_pipeline import DeepAnalysisPipeline, DeepAnalysisResult
from services.market_scanner import ScanResult, ScannerFunnelMetrics, ScreeningResult
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider
from services.stock_decision import StockDecision
from services.today_opportunities import TodayOpportunitiesService


def _scanner_result(symbol: str, rank: int = 1) -> ScreeningResult:
    return ScreeningResult(
        symbol=symbol,
        instrument_key=f"NSE_EQ|{symbol}",
        passed=True,
        score=80,
        signals={
            "trend": True,
            "momentum": True,
            "liquidity": True,
            "support_resistance": True,
            "breakout_breakdown": True,
            "volatility": True,
        },
        reason_codes=("trend_signal", "momentum_signal"),
        provider="upstox",
    )


class _Scanner:
    def __init__(self, symbols: tuple[str, ...]):
        self.symbols = symbols

    def scan(self) -> ScanResult:
        results = tuple(_scanner_result(symbol) for symbol in self.symbols)
        return ScanResult(
            results=results,
            metrics=ScannerFunnelMetrics(
                universe_count=2656,
                data_available_count=2500,
                liquidity_pass_count=100,
                trend_pass_count=80,
                momentum_pass_count=60,
                technical_pass_count=len(results),
                final_candidate_count=len(results),
            ),
        )


def _deep_result(symbol: str, action: str = "Wait") -> DeepAnalysisResult:
    return DeepAnalysisResult(
        snapshot={"symbol": symbol, "name": symbol, "price": 100.0, "changePct": 1.0},
        insight={"support": 90.0, "resistance": 110.0, "aiInsight": "test", "series": []},
        legacy_analysis=SimpleNamespace(
            symbol=symbol,
            strength_score=80,
            stars=4,
            classification="Strong Watch",
            trade_setup="Breakout",
            risk_level="Medium",
            suggested_action=action,
            insight="technical test",
        ),
        decision=StockDecision(
            recommendation=SimpleNamespace(action=action),
            trend="bullish",
            score=80,
        ),
        snapshot_provider="upstox",
        insight_provider="upstox",
    )


def test_discovery_result_preserves_funnel_and_non_curated_candidates() -> None:
    pipeline = TodayOpportunitiesService(
        MarketDataService(SeedProvider(), SeedProvider()),
        scanner=_Scanner(("VOLTAS", "PIDILITIND")),
        deep_analysis=DeepAnalysisPipeline(analyzer=lambda symbol: _deep_result(symbol)),
    )

    result = pipeline.run()

    assert result.source_mode == "discovery"
    assert result.scan.metrics.universe_count == 2656
    assert [item.ranked.symbol for item in result.discovered] == ["PIDILITIND", "VOLTAS"]
    assert all(item.deep_analysis is not None for item in result.discovered)


def test_high_priority_candidate_can_preserve_wait_recommendation() -> None:
    pipeline = TodayOpportunitiesService(
        MarketDataService(SeedProvider(), SeedProvider()),
        scanner=_Scanner(("VOLTAS",)),
        deep_analysis=DeepAnalysisPipeline(analyzer=lambda symbol: _deep_result(symbol, "Wait")),
    )

    result = pipeline.run()

    assert result.discovered[0].ranked.opportunity_score == 100.0
    assert result.discovered[0].deep_analysis.decision.recommendation.action == "Wait"


def test_discovery_failure_has_explicit_curated_fallback(monkeypatch) -> None:
    class BrokenScanner:
        def scan(self):
            raise RuntimeError("scanner unavailable")

    fallback = SimpleNamespace(
        rows=(),
        action_counts={},
        screening=SimpleNamespace(universe_size=40, eligible_count=40),
        analysed_count=0,
    )
    service = TodayOpportunitiesService(
        MarketDataService(SeedProvider(), SeedProvider()),
        scanner=BrokenScanner(),
        fallback_selector=lambda service: (fallback, {"provider": "seed"}),
    )

    result = service.run()

    assert result.source_mode == "curated_fallback"
    assert result.fallback is fallback
    assert result.error == "scanner unavailable"


def test_slow_discovery_is_bounded_without_fabricating_results() -> None:
    class SlowScanner:
        def scan(self):
            time.sleep(0.2)
            raise RuntimeError("slow scanner")

    service = TodayOpportunitiesService(
        MarketDataService(SeedProvider(), SeedProvider()),
        scanner=SlowScanner(),
    )
    service.SCAN_TIMEOUT_SECONDS = 0.01
    started = time.monotonic()

    result = service.run()

    assert time.monotonic() - started < 0.1
    assert result.source_mode == "discovery_failed"
    assert result.discovered == ()
    assert result.error == "broad-market discovery exceeded its execution deadline"

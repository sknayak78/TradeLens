"""ER-0014B: the Recommendation Engine is the only trend/score authority.

Every endpoint that publishes a trend or a score is driven here with snapshots
whose *seeded* trend and score deliberately contradict their own indicators, so
a payload that leaked provider metadata could not pass.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import pytest

import routers.market as market_router
import routers.watchlist as watchlist_router
from indicators.vwap import calculate_rolling_vwap
from recommendation.config import ACTIONS
from schemas import Ranking, StockDetail, WatchlistAnalysis
from services.market_data_provider import MarketDataProvider
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider
from services.stock_decision import decide

#: Seeded values that must never reach the payload: every snapshot below claims
#: to be a top-scoring uptrend regardless of what its indicators say.
STALE_METADATA: Dict[str, Any] = {"trend": "bullish", "score": 88, "vwap": 9_999.0}

#: One snapshot per recommendation state, so consistency is proven across the
#: full range of engine outputs rather than one happy path.
SNAPSHOTS: Dict[str, Dict[str, Any]] = {
    "Strong Buy": {
        "price": 110.0, "ema20": 105.0, "ema50": 100.0, "ema200": 90.0,
        "rsi": 60.0, "support": 100.0, "resistance": 120.0,
    },
    "Buy": {
        "price": 110.0, "ema20": 105.0, "ema50": 100.0, "ema200": 90.0,
        "rsi": 50.0, "support": 100.0, "resistance": 125.0,
    },
    "Watch": {
        "price": 110.0, "ema20": 105.0, "ema50": 100.0, "ema200": 90.0,
        "rsi": 85.0, "support": 100.0, "resistance": 125.0,
    },
    "Wait": {
        "price": 102.0, "ema20": 105.0, "ema50": 100.0, "ema200": 90.0,
        "rsi": 45.0, "support": 95.0, "resistance": 104.0,
    },
    "Avoid": {
        "price": 80.0, "ema20": 105.0, "ema50": 100.0, "ema200": 90.0,
        "rsi": 25.0, "support": 70.0, "resistance": 95.0,
    },
}


def _row(action: str) -> Dict[str, Any]:
    """A provider row for `action`, carrying contradictory seeded metadata."""
    return {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "changePct": 1.24,
        "volume": 4_820_000,
        "avg_volume": 4_097_000,
        "day_high": SNAPSHOTS[action]["price"],
        "sector": "Energy",
        **STALE_METADATA,
        **SNAPSHOTS[action],
    }


class _RowProvider(MarketDataProvider):
    """Serves one crafted row for every symbol, with no network access."""

    name = "row_stub"

    def __init__(self, row: Dict[str, Any]):
        self._row = row
        self._seed = SeedProvider()

    def get_market_summary(self) -> Dict[str, Any]:
        return self._seed.get_market_summary()

    def get_stock(self, symbol: str) -> Optional[Dict[str, Any]]:
        return {**self._row, "symbol": symbol}

    def get_stock_insight(self, symbol: str) -> Dict[str, Any]:
        return {
            "support": self._row["support"],
            "resistance": self._row["resistance"],
            "aiInsight": "test",
            "series": [{"t": "2024-01-01", "v": self._row["price"]}],
        }

    def search_stocks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return [self.get_stock("RELIANCE")]

    def get_opportunities(self) -> List[Dict[str, Any]]:
        return [{"symbol": "RELIANCE", "reason": "curated reason"}]

    def get_all_stocks(self) -> List[Dict[str, Any]]:
        return [self.get_stock("RELIANCE")]

    def get_default_watchlist_symbols(self) -> List[str]:
        return ["RELIANCE"]


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch):
    """Point both routers at a crafted row and return the payload builders."""

    def _serve(action: str) -> None:
        provider = _RowProvider(_row(action))
        service = MarketDataService(
            primary_provider=provider, fallback_provider=provider
        )
        monkeypatch.setattr(market_router, "market_data_service", service)
        monkeypatch.setattr(watchlist_router, "market_data_service", service)

    return _serve


# ---------- Requirement 5: nothing may contradict the recommendation ----------

@pytest.mark.parametrize("action", ACTIONS)
def test_stock_detail_parent_trend_and_score_mirror_the_recommendation(
    action: str, served
) -> None:
    served(action)
    payload: StockDetail = market_router.stock_detail("RELIANCE")

    assert payload.recommendation is not None
    assert payload.recommendation.action == action
    assert payload.trend == payload.recommendation.trend
    assert payload.score == payload.recommendation.score
    # ...and the seeded score literal never reaches the payload.
    assert payload.score != STALE_METADATA["score"]


@pytest.mark.parametrize("action", ACTIONS)
def test_watchlist_row_trend_and_score_mirror_the_recommendation(
    action: str, served
) -> None:
    served(action)
    expected = decide(_row(action))
    row: WatchlistAnalysis = watchlist_router._enrich("RELIANCE")

    assert row.trend == expected.trend
    assert row.score == expected.score
    assert row.score != STALE_METADATA["score"]


@pytest.mark.parametrize("action", ACTIONS)
def test_rankings_and_catalog_trends_mirror_the_recommendation(
    action: str, served
) -> None:
    served(action)
    expected = decide(_row(action))

    rankings: List[Ranking] = market_router.opportunities()
    catalog = market_router.list_stocks()

    assert [r.trend for r in rankings] == [expected.trend]
    assert [s.trend for s in catalog] == [expected.trend]
    assert rankings[0].action == expected.recommendation.action
    assert rankings[0].strategy == expected.recommendation.strategy
    # Legacy analysis chips remain present (may disagree with mentor authority).
    assert rankings[0].tradeSetup
    assert rankings[0].suggestedAction


def test_a_bearish_stock_is_never_published_as_the_seeded_uptrend(served) -> None:
    """The regression ER-0014B exists for: bearish engine, "bullish" provider."""
    served("Avoid")
    payload = market_router.stock_detail("RELIANCE")

    assert payload.recommendation is not None
    assert payload.recommendation.trend == "bearish"
    assert payload.trend == "bearish"
    assert payload.score == payload.recommendation.score
    assert payload.score < STALE_METADATA["score"]


def test_an_unusable_snapshot_publishes_no_direction(served) -> None:
    decision = decide({"symbol": "RELIANCE", **STALE_METADATA})

    assert decision.recommendation is None
    assert (decision.trend, decision.score) == ("neutral", 0)


# ---------- Requirement 3: stale provider metadata ----------

def test_vwap_is_recomputed_from_live_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seeded VWAP literal must not survive a live fetch."""
    provider = YahooFinanceProvider(SeedProvider())
    history = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(20)],
            "High": [101.0 + i for i in range(20)],
            "Low": [99.0 + i for i in range(20)],
            "Close": [100.5 + i for i in range(20)],
            "Volume": [1000 + i for i in range(20)],
        },
        index=pd.date_range("2024-01-01", periods=20, freq="D"),
    )
    monkeypatch.setattr(
        provider, "_history", lambda symbol, period="2d", interval="1d": history
    )
    monkeypatch.setattr(provider, "_quote", lambda symbol: (3001.25, 1.5, 123456))

    seeded_vwap = SeedProvider().get_stock("RELIANCE")["vwap"]
    stock = provider.get_stock("RELIANCE")

    assert stock is not None
    assert stock["vwap"] != seeded_vwap
    assert stock["vwap"] == 109.7  # volume-weighted mean of the 20 typical prices


def test_a_failed_live_fetch_leaves_the_row_internally_consistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On fallback the whole row is seeded, so its VWAP matches its own price."""
    provider = YahooFinanceProvider(SeedProvider())
    monkeypatch.setattr(
        provider,
        "_history",
        lambda symbol, period="2d", interval="1d": (_ for _ in ()).throw(
            RuntimeError("Yahoo unavailable")
        ),
    )

    stock = provider.get_stock("RELIANCE")
    seeded = SeedProvider().get_stock("RELIANCE")

    assert stock is not None
    assert stock["vwap"] == seeded["vwap"]
    assert stock["price"] == seeded["price"]


# ---------- The VWAP indicator itself ----------

def test_rolling_vwap_weights_by_volume() -> None:
    # Two bars, the second with nine times the volume: the mean must sit near it.
    vwap = calculate_rolling_vwap(
        highs=[10.0, 20.0], lows=[10.0, 20.0], closes=[10.0, 20.0],
        volumes=[100.0, 900.0],
    )

    assert vwap == pytest.approx(19.0)


def test_rolling_vwap_only_reads_the_requested_window() -> None:
    vwap = calculate_rolling_vwap(
        highs=[1.0, 1.0, 30.0], lows=[1.0, 1.0, 30.0], closes=[1.0, 1.0, 30.0],
        volumes=[500.0, 500.0, 1.0], period=1,
    )

    assert vwap == pytest.approx(30.0)


def test_rolling_vwap_falls_back_to_the_unweighted_mean_without_volume() -> None:
    vwap = calculate_rolling_vwap(
        highs=[10.0, 20.0], lows=[10.0, 20.0], closes=[10.0, 20.0],
        volumes=[0.0, 0.0],
    )

    assert vwap == pytest.approx(15.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"period": 0},
        {"volumes": [1.0]},
    ],
)
def test_rolling_vwap_rejects_unusable_input(kwargs: Dict[str, Any]) -> None:
    call = {
        "highs": [1.0, 2.0], "lows": [1.0, 2.0], "closes": [1.0, 2.0],
        "volumes": [1.0, 1.0], **kwargs,
    }

    with pytest.raises(ValueError):
        calculate_rolling_vwap(**call)


# ---------- Requirement 4: legacy fields deprecated, still served ----------

LEGACY_FIELDS = (
    "suggestedAction", "classification", "insight", "tradeSetup", "riskLevel",
    "strengthScore", "stars",
)


@pytest.mark.parametrize("field", LEGACY_FIELDS)
def test_legacy_fields_are_marked_deprecated_but_still_present(
    field: str, served
) -> None:
    served("Buy")
    payload = market_router.stock_detail("RELIANCE").model_dump()

    assert field in payload
    assert StockDetail.model_fields[field].deprecated

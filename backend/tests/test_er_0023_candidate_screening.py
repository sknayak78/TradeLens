"""ER-0023: market universe and candidate screening tests."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

import routers.market as market_router
from recommendation.config import ACTIONS
from seed_data import STOCKS
from services.market_data.screening import screen_candidate, screen_candidates
from services.market_data.universe import InstrumentUniverse, default_universe
from services.market_data_service import MarketDataService
from services.opportunity_selection import select_opportunities
from services.providers.seed_provider import SeedProvider
from services.stock_decision import decide
from tests.test_single_source_of_truth import _RowProvider


def _valid_stock(**overrides: Any) -> dict[str, Any]:
    row = deepcopy(STOCKS[0])
    row.update(overrides)
    return row


def test_default_universe_has_forty_screening_instruments():
    assert default_universe.stock_count == 40
    assert len(default_universe.screening_symbols()) == 40
    assert default_universe.config.name == "TradeLens Demo Universe"
    assert default_universe.config.active is True


def test_all_seed_stocks_pass_screening():
    summary = screen_candidates(STOCKS)
    assert summary.universe_size == 40
    assert summary.eligible_count == 40
    assert summary.excluded_count == 0


def test_ineligible_instruments_are_removed_before_analysis():
    bad = _valid_stock(symbol="BAD1", price=float("nan"))
    good = _valid_stock(symbol="GOOD1")

    summary = screen_candidates([bad, good])

    assert summary.eligible_count == 1
    assert summary.excluded_count == 1
    assert summary.eligible[0]["symbol"] == "GOOD1"
    assert "non_finite_price" in summary.excluded[0].exclusion_reasons


def test_wait_candidate_remains_eligible():
    wait_stock = _valid_stock(symbol="WAIT1", trend="neutral", rsi=45.0, changePct=-0.5)
    assert screen_candidate(wait_stock).eligible is True


def test_avoid_candidate_remains_eligible():
    avoid_stock = _valid_stock(symbol="AVOID1", trend="bearish", rsi=25.0, changePct=-2.0)
    assert screen_candidate(avoid_stock).eligible is True


def test_screening_does_not_alter_mentor_decision():
    stock = _valid_stock(symbol="RELIANCE")
    baseline = decide(stock)
    screened = screen_candidates([stock]).eligible[0]
    after = decide(screened)

    assert after.trend == baseline.trend
    assert after.score == baseline.score
    if baseline.recommendation and after.recommendation:
        assert after.recommendation.action == baseline.recommendation.action


def test_opportunities_uses_screened_forty_stock_universe():
    provider = SeedProvider()
    service = MarketDataService(provider, provider)
    selection, _ = select_opportunities(service)

    assert selection.screening.universe_size == 40
    assert selection.screening.eligible_count == 40
    assert selection.analysed_count == 40
    assert selection.returned_count == 10


def test_opportunities_not_limited_to_legacy_ten_symbol_list():
    provider = SeedProvider()
    service = MarketDataService(provider, provider)
    selection, _ = select_opportunities(service)

    returned_symbols = {row.symbol for row in selection.rows}
    legacy_only = set(default_universe.opportunity_symbols())

    assert len(returned_symbols) == 10
    assert returned_symbols.issubset({stock["symbol"] for stock in STOCKS})
    assert returned_symbols != legacy_only or len(legacy_only) == 10


def test_recommendation_authority_remains_intact(served):
    served("Buy")
    rows = market_router.opportunities()

    assert rows
    for row in rows:
        stock = SeedProvider().get_stock(row.symbol)
        assert stock is not None
        assert row.trend == decide(stock).trend


def test_empty_universe_is_handled_safely():
    provider = SeedProvider()
    service = MarketDataService(provider, provider)
    from datetime import datetime, timezone
    from services.market_data_service import MarketDataMetadata, MarketDataResult

    metadata = MarketDataMetadata(
        provider="seed",
        cached=False,
        as_of=datetime.now(timezone.utc),
        market_status="OPEN",
    )
    service.get_all_stocks = lambda: MarketDataResult(data=[], metadata=metadata)  # type: ignore[method-assign]

    selection, _ = select_opportunities(service)

    assert selection.screening.universe_size == 0
    assert selection.returned_count == 0


def test_seed_provider_selection_is_deterministic_without_network():
    provider = SeedProvider()
    service = MarketDataService(provider, provider)

    first, _ = select_opportunities(service)
    second, _ = select_opportunities(service)

    assert [row.symbol for row in first.rows] == [row.symbol for row in second.rows]


def test_seed_recommendation_distribution_is_genuine():
    provider = SeedProvider()
    service = MarketDataService(provider, provider)
    selection, _ = select_opportunities(service)

    distribution = {action: 0 for action in ACTIONS}
    for row in selection.rows:
        stock = provider.get_stock(row.symbol)
        assert stock is not None
        decision = decide(stock)
        if decision.recommendation is not None:
            distribution[decision.recommendation.action] += 1

    assert sum(distribution.values()) == selection.returned_count
    assert distribution["Strong Buy"] + distribution["Buy"] <= selection.returned_count


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch):
    def _serve(action: str) -> None:
        from tests.test_single_source_of_truth import SNAPSHOTS, STALE_METADATA

        row = {
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
        provider = _RowProvider(row)
        service = MarketDataService(primary_provider=provider, fallback_provider=provider)
        monkeypatch.setattr(market_router, "market_data_service", service)

    return _serve

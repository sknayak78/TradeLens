"""ER-006: technical entry quality must not masquerade as investment judgment."""
from __future__ import annotations

from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationInput


engine = RecommendationEngine()


def test_torrent_like_healthy_trend_with_poor_entry_waits() -> None:
    recommendation = engine.recommend(
        RecommendationInput(
            symbol="TORRENTLIKE",
            price=1305.90,
            ema20=1285.22,
            ema50=1250.00,
            ema200=1100.00,
            rsi=45.0,
            support=1199.00,
            resistance=1327.40,
        )
    )

    assert recommendation.trend == "bullish"
    assert recommendation.strategy == "Breakout"
    assert recommendation.action == "Wait"
    assert "limited upside" in recommendation.verdict
    assert "not a stock" not in recommendation.verdict.lower()
    assert "fresh entry" in recommendation.summary.lower()


def test_broken_technical_setup_retains_avoid_without_broad_stock_claim() -> None:
    recommendation = engine.recommend(
        RecommendationInput(
            symbol="BROKENLIKE",
            price=80.0,
            ema20=100.0,
            ema50=110.0,
            ema200=120.0,
            rsi=35.0,
            support=70.0,
            resistance=95.0,
        )
    )

    assert recommendation.trend == "bearish"
    assert recommendation.strategy == "No Entry Yet"
    assert recommendation.action == "Avoid"
    assert "technical setup" in recommendation.verdict.lower()
    assert "not a stock" not in recommendation.verdict.lower()


def test_bearish_explanation_matches_long_term_indicator_state() -> None:
    recommendation = engine.recommend(
        RecommendationInput(
            symbol="BROKENLIKE",
            price=80.0,
            ema20=100.0,
            ema50=110.0,
            ema200=120.0,
        )
    )

    assert "lost its long-term average" in " ".join(recommendation.why)
    assert "larger trend is down" in " ".join(recommendation.why)

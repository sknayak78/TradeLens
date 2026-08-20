"""Mentor Engine — stable Trading Setup + daily Setup Progress.

TradeLens tracks a setup like an experienced mentor: structure defines the plan,
and the last price only updates progress against that plan.

Pipeline::

    score → structure → TradingSetup → SetupProgress → action → narrative

Public ``Recommendation`` fields remain stable for API consumers; ``setup`` and
``progress`` are additive.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional, Tuple

from . import narrative
from .config import (
    BEGINNER_TIPS,
    CONFIDENCE_BANDS,
    CONFIDENCE_CEILING,
    CONVICTION_BANDS,
    HOLDING_PERIODS,
    IDEAL_FOR,
    INDICATOR_LABELS,
    LEVEL_STRATEGIES,
    MAX_SCORE,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SCORING_RULES,
)
from .models import (
    Action,
    Conviction,
    DataQuality,
    Recommendation,
    RecommendationInput,
    TradeLevels,
    Trend,
)
from .progress import SetupProgress, action_from_progress, evaluate_progress
from .setup import TradingSetup, build_setup
from .structure import structural_trend

logger = logging.getLogger("tradelens.recommendation")

_POSITIVE_ACTIONS: Tuple[Action, ...] = ("Strong Buy", "Buy", "Watch")


def _event(event: str, **fields: Any) -> str:
    return json.dumps({"event": event, **fields}, sort_keys=True)


class RecommendationEngine:
    """Mentor Engine: structure-stable setups with daily progress."""

    def recommend(self, market: RecommendationInput) -> Recommendation:
        rules_matched, score = self._score(market)
        setup = build_setup(market, rules_matched, score)
        progress = evaluate_progress(market, setup)
        action = action_from_progress(setup, progress)  # type: ignore[assignment]
        # Legacy levels field: only strategies whose UI shows a buy-now zone.
        public_levels = (
            setup.levels if setup.strategy in LEVEL_STRATEGIES else None
        )

        story = narrative.build(
            market=market,
            trend=setup.trend,
            action=action,
            strategy=setup.strategy,
            score=score,
            rules_matched=rules_matched,
            levels=public_levels,
            limits=setup.limits,
            progress=progress,
            setup=setup,
        )
        summary = story.summary

        recommendation = Recommendation(
            symbol=market.symbol,
            action=action,
            strategy=setup.strategy,
            verdict=story.verdict,
            summary=summary,
            conviction=self._conviction(score),
            score=score,
            trend=setup.trend,
            confidence=self._confidence(market, action, score),
            data_quality=self._data_quality(market),
            holding_period=HOLDING_PERIODS[action],
            next_trigger=progress.next_event,
            beginner_tip=BEGINNER_TIPS[action],
            ideal_for=IDEAL_FOR[action],
            entry_condition=story.entry_condition,
            rationale=summary,
            why=story.why,
            positives=story.positives,
            risks=story.risks,
            rules_matched=rules_matched,
            warnings=self._warnings(market, setup),
            levels=public_levels,
            setup=setup,
            progress=progress,
        )
        logger.debug(_event(
            "recommendation.generated",
            symbol=recommendation.symbol,
            action=recommendation.action,
            strategy=recommendation.strategy,
            progress=progress.status,
            score=recommendation.score,
            trend=recommendation.trend,
            structure_key=setup.structure_key,
        ))
        return recommendation

    def recommend_many(
        self, markets: List[RecommendationInput]
    ) -> List[Recommendation]:
        return [self.recommend(market) for market in markets]

    def _score(self, market: RecommendationInput) -> Tuple[List[str], int]:
        matched: List[str] = []
        score = 0
        for rule in SCORING_RULES:
            if rule.check(market):
                matched.append(rule.key)
                score += rule.points
        return matched, min(score, MAX_SCORE)

    def _conviction(self, score: int) -> Conviction:
        for band in CONVICTION_BANDS:
            if score >= band["min"]:
                return band["label"]
        return CONVICTION_BANDS[-1]["label"]

    def _confidence(
        self, market: RecommendationInput, action: Action, score: int
    ) -> float:
        low, high = CONFIDENCE_BANDS[action]
        setup_strength = score / MAX_SCORE
        if action not in _POSITIVE_ACTIONS:
            setup_strength = 1.0 - setup_strength
        evidence = 0.5 * setup_strength + 0.5 * market.completeness
        return round(min(low + (high - low) * evidence, CONFIDENCE_CEILING), 2)

    def _data_quality(self, market: RecommendationInput) -> DataQuality:
        return "Complete" if not market.missing_indicators else "Partial"

    def _trend(self, market: RecommendationInput) -> Trend:
        """Kept for tests that call the private helper directly."""
        return structural_trend(market)

    def _warnings(self, market: RecommendationInput, setup: TradingSetup) -> List[str]:
        warnings: List[str] = []
        missing = market.missing_indicators
        if missing:
            labels = ", ".join(INDICATOR_LABELS[name] for name in missing)
            warnings.append(
                f"partial_data: {labels} unavailable, so this recommendation is "
                "based on an incomplete indicator set."
            )
        if market.rsi is not None:
            if market.rsi >= RSI_OVERBOUGHT:
                warnings.append("rsi_overbought")
            elif market.rsi <= RSI_OVERSOLD:
                warnings.append("rsi_oversold")
        if market.resistance is not None and market.price >= market.resistance:
            warnings.append("price_at_or_above_resistance")
        if "no_levels" in setup.limits:
            warnings.append("no_usable_levels")
        if "poor_risk_reward" in setup.limits:
            warnings.append("risk_reward_below_minimum")
        return warnings


engine = RecommendationEngine()

"""RecommendationEngine — deterministic trade recommendations from live indicators.

The engine is pure: no network access, no database access, no LLM, no clock or
randomness.  It consumes a :class:`~recommendation.models.RecommendationInput`
(price, EMA20/50/200, RSI, support, resistance) and returns a
:class:`~recommendation.models.Recommendation` describing an action, its
conviction, the derived trend, long trade levels and a short rationale.

Trend is derived from the EMA stack rather than taken from any snapshot field so
seeded trend values cannot influence the outcome.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional, Tuple

from .config import (
    ACTION_BUY_MIN_SCORE,
    ACTION_WAIT_MIN_SCORE,
    ACTION_WATCH_MIN_SCORE,
    CONVICTION_BANDS,
    MAX_SCORE,
    MAX_STOP_DISTANCE_PCT,
    MIN_HEADROOM_PCT,
    MIN_RISK_REWARD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SCORING_RULES,
    SECOND_TARGET_EXTENSION,
    STOP_BUFFER_PCT,
)
from .models import (
    Action,
    Conviction,
    Recommendation,
    RecommendationInput,
    TradeLevels,
    Trend,
)

logger = logging.getLogger("tradelens.recommendation")

_BUY_ACTIONS: Tuple[Action, ...] = ("Buy", "Buy on Breakout")


def _event(event: str, **fields: Any) -> str:
    """Serialize operational fields consistently for standard Python logging."""
    return json.dumps({"event": event, **fields}, sort_keys=True)


class RecommendationEngine:
    """Rule-based recommendation engine for a single live indicator snapshot."""

    def recommend(self, market: RecommendationInput) -> Recommendation:
        rules_matched, score = self._score(market)
        trend = self._trend(market)
        warnings = self._warnings(market)
        levels = self._levels(market)
        action = self._action(market, trend, score)

        if action in _BUY_ACTIONS and levels is None:
            # Without a stop and a target there is nothing actionable to give.
            action = "Watch"
            warnings.append("no_usable_levels")
        elif (
            action == "Buy"
            and levels is not None
            and levels.risk_reward < MIN_RISK_REWARD
        ):
            # Breakout entries are priced above resistance, so the reward:risk
            # gate only applies to an immediate entry at the last price.
            action = "Watch"
            warnings.append("risk_reward_below_minimum")

        recommendation = Recommendation(
            symbol=market.symbol,
            action=action,
            conviction=self._conviction(score),
            score=score,
            trend=trend,
            confidence=self._confidence(market, score),
            rationale=self._rationale(market, trend, action, rules_matched),
            rules_matched=rules_matched,
            warnings=warnings,
            levels=None if action == "Avoid" else levels,
        )
        logger.debug(_event(
            "recommendation.generated",
            symbol=recommendation.symbol,
            action=recommendation.action,
            score=recommendation.score,
            trend=recommendation.trend,
        ))
        return recommendation

    def recommend_many(
        self, markets: List[RecommendationInput]
    ) -> List[Recommendation]:
        return [self.recommend(market) for market in markets]

    # ---------- Scoring ----------

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

    def _confidence(self, market: RecommendationInput, score: int) -> float:
        """Blend indicator completeness with rule strength into a 0-1 value."""
        strength = 0.5 + 0.5 * (score / MAX_SCORE)
        return round(market.completeness * strength, 2)

    # ---------- Trend (EMA stack only) ----------

    def _trend(self, market: RecommendationInput) -> Trend:
        emas = [
            value
            for value in (market.ema20, market.ema50, market.ema200)
            if value is not None
        ]
        if not emas:
            return "neutral"
        above = sum(1 for ema in emas if market.price > ema)
        if above == len(emas):
            return "bullish"
        if above == 0:
            return "bearish"
        return "neutral"

    # ---------- Warnings ----------

    def _warnings(self, market: RecommendationInput) -> List[str]:
        warnings: List[str] = []
        missing = [
            name
            for name in RecommendationInput.OPTIONAL_FIELDS
            if getattr(market, name) is None
        ]
        if missing:
            warnings.append("missing_indicators:" + ",".join(missing))
        if market.rsi is not None:
            if market.rsi >= RSI_OVERBOUGHT:
                warnings.append("rsi_overbought")
            elif market.rsi <= RSI_OVERSOLD:
                warnings.append("rsi_oversold")
        if market.resistance is not None and market.price >= market.resistance:
            warnings.append("price_at_or_above_resistance")
        return warnings

    # ---------- Trade levels ----------

    def _levels(self, market: RecommendationInput) -> Optional[TradeLevels]:
        if not market.has_valid_levels:
            return None
        support = market.support
        resistance = market.resistance
        if support is None or resistance is None or resistance <= market.price:
            return None

        entry = market.price
        support_stop = support * (1 - STOP_BUFFER_PCT / 100)
        hard_floor = entry * (1 - MAX_STOP_DISTANCE_PCT / 100)
        stop_loss = max(support_stop, hard_floor)
        if stop_loss >= entry:
            return None

        target1 = resistance
        target2 = entry + (target1 - entry) * SECOND_TARGET_EXTENSION
        risk_reward = (target1 - entry) / (entry - stop_loss)
        return TradeLevels(
            entry=round(entry, 2),
            stop_loss=round(stop_loss, 2),
            target1=round(target1, 2),
            target2=round(target2, 2),
            risk_reward=round(risk_reward, 2),
        )

    # ---------- Action ----------

    def _action(
        self, market: RecommendationInput, trend: Trend, score: int
    ) -> Action:
        if trend == "bearish":
            return "Avoid"
        if market.rsi is not None and market.rsi >= RSI_OVERBOUGHT:
            return "Wait"
        if score >= ACTION_BUY_MIN_SCORE and trend == "bullish":
            headroom = market.headroom_pct
            if headroom is not None and headroom >= MIN_HEADROOM_PCT:
                return "Buy"
            return "Buy on Breakout"
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        if score >= ACTION_WAIT_MIN_SCORE:
            return "Wait"
        return "Avoid"

    # ---------- Rationale (template-based, no LLM) ----------

    def _rationale(
        self,
        market: RecommendationInput,
        trend: Trend,
        action: Action,
        rules_matched: List[str],
    ) -> str:
        parts: List[str] = []

        # Line 1 — location relative to the EMA stack.
        if "ema_stack_bullish" in rules_matched:
            parts.append("EMA20 > EMA50 > EMA200 confirms an uptrend.")
        elif trend == "bullish":
            parts.append("Price holds above its available EMAs.")
        elif trend == "bearish":
            parts.append("Price is below every available EMA.")
        else:
            parts.append("Price is mixed against its EMAs.")

        # Line 2 — momentum via RSI.
        if market.rsi is None:
            parts.append("RSI is unavailable.")
        elif market.rsi >= RSI_OVERBOUGHT:
            parts.append("RSI is overbought; momentum is stretched.")
        elif "rsi_healthy" in rules_matched:
            parts.append("RSI sits in the healthy 55-70 zone.")
        elif market.rsi <= RSI_OVERSOLD:
            parts.append("RSI is oversold; momentum is weak.")
        else:
            parts.append("Momentum is neutral.")

        # Line 3 — level structure.
        headroom = market.headroom_pct
        cushion = market.support_cushion_pct
        if headroom is not None and cushion is not None:
            parts.append(
                f"Resistance is {headroom:.1f}% away with "
                f"{cushion:.1f}% cushion above support."
            )
        else:
            parts.append("Support and resistance levels are incomplete.")

        # Line 4 — actionable close.
        if action == "Buy":
            parts.append("Enter now and trail the stop below support.")
        elif action == "Buy on Breakout":
            parts.append("Wait for a close above resistance before entering.")
        elif action == "Watch":
            parts.append("Track it for a cleaner entry.")
        elif action == "Wait":
            parts.append("Wait for momentum to reset.")
        else:
            parts.append("Avoid this setup for now.")

        text = " ".join(parts)
        words = text.split()
        if len(words) > 60:
            text = " ".join(words[:60])
            if not text.endswith("."):
                text += "."
        return text


# Module-level singleton — pure functions, thread-safe.
engine = RecommendationEngine()

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
import math
from typing import Any, List, Optional, Tuple

from .config import (
    ACTION_BUY_MIN_SCORE,
    ACTION_STRONG_BUY_MIN_SCORE,
    ACTION_WAIT_MIN_SCORE,
    ACTION_WATCH_MIN_SCORE,
    CONVICTION_BANDS,
    HOLDING_PERIODS,
    INDICATOR_LABELS,
    MAX_SCORE,
    MIN_HEADROOM_PCT,
    MIN_RISK_REWARD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SCORING_RULES,
    SECOND_TARGET_BAND_SHARE,
    STOP_SUPPORT_MULTIPLIER,
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

logger = logging.getLogger("tradelens.recommendation")

_BUY_ACTIONS: Tuple[Action, ...] = ("Strong Buy", "Buy", "Buy on Breakout")
_FRESH_ENTRY_ACTIONS: Tuple[Action, ...] = ("Strong Buy", "Buy")


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
            # Without an entry zone, a stop and a target there is nothing to
            # enter; an extended winner is still holdable, missing data is not.
            warnings.append("no_usable_levels")
            action = self._downgrade(trend, score)
        elif (
            action in _FRESH_ENTRY_ACTIONS
            and levels is not None
            and levels.risk_reward < MIN_RISK_REWARD
        ):
            # Breakout entries are priced above resistance, so the reward:risk
            # gate only applies to an immediate entry inside the zone.
            warnings.append("risk_reward_below_minimum")
            action = self._downgrade(trend, score)

        recommendation = Recommendation(
            symbol=market.symbol,
            action=action,
            conviction=self._conviction(score),
            score=score,
            trend=trend,
            confidence=self._confidence(market, score),
            data_quality=self._data_quality(market),
            holding_period=HOLDING_PERIODS[action],
            entry_condition=self._entry_condition(market, action, levels),
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

    def _data_quality(self, market: RecommendationInput) -> DataQuality:
        return "Complete" if not market.missing_indicators else "Partial"

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
        return warnings

    # ---------- Trade levels ----------

    def _levels(self, market: RecommendationInput) -> Optional[TradeLevels]:
        if not market.has_valid_levels:
            return None
        support = market.support
        resistance = market.resistance
        if support is None or resistance is None or resistance <= market.price:
            return None

        # Entry zone: pull back to the higher of EMA20 and support, buy up to
        # the last price.
        entry_max = market.price
        entry_min = support if market.ema20 is None else max(market.ema20, support)
        if entry_min >= entry_max:
            return None

        stop_loss = support * STOP_SUPPORT_MULTIPLIER
        if stop_loss >= entry_min:
            return None

        target1 = resistance
        target2 = resistance + SECOND_TARGET_BAND_SHARE * (resistance - support)
        # Measured from the midpoint of the zone — the representative fill.
        entry_reference = (entry_min + entry_max) / 2
        if entry_reference <= stop_loss:
            return None
        risk_reward = (target1 - entry_reference) / (entry_reference - stop_loss)
        computed = (entry_min, entry_max, stop_loss, target1, target2, risk_reward)
        if not all(math.isfinite(value) for value in computed):
            # Levels are all-or-nothing: a partial set is worse than none.
            return None
        return TradeLevels(
            entry_min=round(entry_min, 2),
            entry_max=round(entry_max, 2),
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
            # Stretched momentum rules out a fresh entry, but a healthy trend is
            # still worth holding for anyone already positioned.
            return self._downgrade(trend, score)
        if score >= ACTION_BUY_MIN_SCORE and trend == "bullish":
            headroom = market.headroom_pct
            if headroom is not None and headroom >= MIN_HEADROOM_PCT:
                if score >= ACTION_STRONG_BUY_MIN_SCORE:
                    return "Strong Buy"
                return "Buy"
            return "Buy on Breakout"
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        if score >= ACTION_WAIT_MIN_SCORE:
            return "Wait"
        return "Avoid"

    def _downgrade(self, trend: Trend, score: int) -> Action:
        """Resolve a blocked entry into "Hold" (trend intact) or a wait state.

        Existing holders keep a position while the trend and score still stand;
        otherwise there is nothing to do yet.
        """
        if trend == "bullish" and score >= ACTION_WATCH_MIN_SCORE:
            return "Hold"
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        return "Wait"

    # ---------- Beginner-facing entry condition (template-based, no LLM) ----------

    def _entry_condition(
        self,
        market: RecommendationInput,
        action: Action,
        levels: Optional[TradeLevels],
    ) -> str:
        """Return the one concrete thing a beginner should watch for next."""
        if action in ("Strong Buy", "Buy") and levels is not None:
            return (
                f"Consider entering between {levels.entry_min:.2f} and "
                f"{levels.entry_max:.2f} once the price stabilises, and exit if it "
                f"closes below {levels.stop_loss:.2f}."
            )
        if action == "Buy on Breakout":
            if market.resistance is not None:
                return (
                    "Wait for a daily close above resistance "
                    f"{market.resistance:.2f} before entering."
                )
            return "Wait for a daily close above the recent high before entering."
        if action == "Hold":
            if levels is not None:
                return (
                    "No fresh entry here: hold and reassess if the price closes "
                    f"below {levels.stop_loss:.2f}."
                )
            if market.support is not None:
                return (
                    "No fresh entry here: hold and reassess if the price closes "
                    f"below support {market.support:.2f}."
                )
            return "No fresh entry here: hold and reassess on the next pullback."
        if action == "Watch":
            if levels is not None:
                return (
                    "Wait for the price to pull back into "
                    f"{levels.entry_min:.2f}-{levels.entry_max:.2f} and hold there."
                )
            if market.ema20 is not None:
                return (
                    f"Wait for the price to stabilise near EMA20 {market.ema20:.2f} "
                    "before considering an entry."
                )
            return "Wait for clearer support and resistance levels before acting."
        if action == "Wait":
            if market.rsi is not None and market.rsi >= RSI_OVERBOUGHT:
                return "Wait for momentum to cool: RSI is above 80."
            return "Wait for the setup to strengthen before considering an entry."
        return "No trade: stay out until the price reclaims its moving averages."

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
        if action in ("Strong Buy", "Buy"):
            parts.append("Buy inside the entry zone and trail the stop below support.")
        elif action == "Buy on Breakout":
            parts.append("Wait for a close above resistance before entering.")
        elif action == "Hold":
            parts.append("Existing holders can stay; no fresh entry here.")
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

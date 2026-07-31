"""StockAnalysisService — lightweight, rule-based intraday analysis.

Given a market snapshot (price, ema20, vwap, rsi, volume, avg_volume,
day_high, trend) the service returns:

- trend           (bullish / bearish / neutral)
- strength_score  (0-100)
- stars           (2-5)
- classification  (Excellent / Strong Watch / Watch / Ignore)
- trade_setup     (Momentum / Breakout / Pullback / Trend Continuation / Consolidation)
- risk_level      (Low / Medium / High)
- suggested_action(Watch / Buy on Breakout / Wait / Avoid)
- insight         (short, template-generated explanation ≤ 60 words)
- rules_matched   (list of rule keys that fired, for transparency)

All calculations are deterministic. No LLM, no I/O.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Literal

from .scoring_config import (
    SCORING_RULES,
    MAX_SCORE,
    CLASSIFICATIONS,
    RISK_LOW_MIN_SCORE,
    RISK_MEDIUM_MIN_SCORE,
    ACTION_BUY_MIN_SCORE,
    ACTION_WATCH_MIN_SCORE,
    ACTION_WAIT_MIN_SCORE,
)


Trend = Literal["bullish", "bearish", "neutral"]
TradeSetup = Literal[
    "Momentum", "Breakout", "Pullback", "Trend Continuation", "Consolidation"
]
RiskLevel = Literal["Low", "Medium", "High"]
Action = Literal["Watch", "Buy on Breakout", "Wait", "Avoid"]


@dataclass
class Analysis:
    symbol: str
    trend: Trend
    strength_score: int
    stars: int
    classification: str
    trade_setup: TradeSetup
    risk_level: RiskLevel
    suggested_action: Action
    insight: str
    rules_matched: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


class StockAnalysisService:
    """Deterministic rule-based analyser for a single stock snapshot."""

    def analyse(self, market: Dict) -> Analysis:
        matched, score = self._score(market)
        classification = self._classify(score)
        setup = self._setup(market, matched)
        risk = self._risk(score, market["trend"])
        action = self._action(score, setup)
        insight = self._insight(market, matched, setup, action)

        return Analysis(
            symbol=market["symbol"],
            trend=market["trend"],
            strength_score=score,
            stars=classification["stars"],
            classification=classification["label"],
            trade_setup=setup,
            risk_level=risk,
            suggested_action=action,
            insight=insight,
            rules_matched=[r for r in matched],
        )

    def analyse_many(self, rows: List[Dict]) -> List[Analysis]:
        return [self.analyse(r) for r in rows]

    # ---------- Scoring ----------

    def _score(self, m: Dict) -> tuple[List[str], int]:
        matched: List[str] = []
        score = 0
        for rule in SCORING_RULES:
            if rule.check(m):
                matched.append(rule.key)
                score += rule.points
        # Clamp defensively — MAX_SCORE is 100 by config.
        return matched, min(score, MAX_SCORE)

    def _classify(self, score: int) -> Dict:
        for c in CLASSIFICATIONS:
            if score >= c["min"]:
                return c
        return CLASSIFICATIONS[-1]

    # ---------- Setup ----------

    def _setup(self, m: Dict, matched: List[str]) -> TradeSetup:
        rsi = m["rsi"]
        price_above_ema = "above_ema20" in matched
        price_above_vwap = "above_vwap" in matched
        volume_hot = "volume_above_avg" in matched
        near_high = "near_day_high" in matched

        # Priority order — exactly one setup wins.
        if price_above_ema and price_above_vwap and rsi >= 65 and volume_hot:
            return "Momentum"
        if near_high and price_above_vwap:
            return "Breakout"
        if price_above_ema and 40.0 <= rsi <= 55.0:
            return "Pullback"
        if m["trend"] == "bullish" and price_above_vwap:
            return "Trend Continuation"
        return "Consolidation"

    # ---------- Risk ----------

    def _risk(self, score: int, trend: Trend) -> RiskLevel:
        if score >= RISK_LOW_MIN_SCORE and trend == "bullish":
            return "Low"
        if score >= RISK_MEDIUM_MIN_SCORE:
            return "Medium"
        return "High"

    # ---------- Suggested action ----------

    def _action(self, score: int, setup: TradeSetup) -> Action:
        if score >= ACTION_BUY_MIN_SCORE and setup in ("Momentum", "Breakout"):
            return "Buy on Breakout"
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        if score >= ACTION_WAIT_MIN_SCORE:
            return "Wait"
        return "Avoid"

    # ---------- Insight (template-based, no LLM) ----------

    def _insight(
        self,
        m: Dict,
        matched: List[str],
        setup: TradeSetup,
        action: Action,
    ) -> str:
        parts: List[str] = []

        # Line 1 — trend location relative to EMA20 / VWAP.
        loc_bits: List[str] = []
        if "above_ema20" in matched:
            loc_bits.append("EMA20")
        if "above_vwap" in matched:
            loc_bits.append("VWAP")
        if loc_bits:
            joined = " and ".join(loc_bits)
            parts.append(f"Price is above {joined}.")
        else:
            parts.append("Price is trading below EMA20 and VWAP.")

        # Line 2 — momentum via RSI.
        rsi = m["rsi"]
        if rsi >= 70:
            parts.append("RSI is overbought; momentum is stretched.")
        elif rsi >= 55:
            parts.append("Momentum is healthy.")
        elif rsi >= 40:
            parts.append("Momentum is neutral.")
        else:
            parts.append("Momentum is weak.")

        # Line 3 — volume.
        if "volume_above_avg" in matched:
            parts.append("Volume is increasing.")
        else:
            parts.append("Volume is below average.")

        # Line 4 — actionable close.
        if setup == "Breakout":
            parts.append("Watch for breakout above today's high.")
        elif setup == "Momentum":
            parts.append("Ride the trend with a trailing stop.")
        elif setup == "Pullback":
            parts.append("Wait for the pullback to hold above support.")
        elif setup == "Trend Continuation":
            parts.append("Look for continuation on the next dip.")
        else:
            parts.append("Wait for a clearer setup to form.")

        # Trim to ≤ 60 words defensively.
        text = " ".join(parts)
        words = text.split()
        if len(words) > 60:
            text = " ".join(words[:60])
            if not text.endswith("."):
                text += "."
        return text


# Module-level singleton — pure functions, thread-safe.
service = StockAnalysisService()

"""Configuration for the TradeLens recommendation engine.

Every threshold used by :mod:`recommendation.engine` lives here so the rules can
be tuned without touching engine code.  Rules are declarative: each one
contributes ``points`` when its ``check`` returns True.  The maximum reachable
score is 100.

Only live, OHLCV-derived indicators are referenced (price, EMA20/50/200, RSI,
support, resistance).  Seeded VWAP / trend / average volume / day high are
deliberately not part of any rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import RecommendationInput


@dataclass(frozen=True)
class Rule:
    key: str
    label: str
    points: int
    check: Callable[[RecommendationInput], bool]


# ---------- Rule predicates ----------

def _price_above_ema20(m: RecommendationInput) -> bool:
    return m.ema20 is not None and m.price > m.ema20


def _price_above_ema50(m: RecommendationInput) -> bool:
    return m.ema50 is not None and m.price > m.ema50


def _price_above_ema200(m: RecommendationInput) -> bool:
    return m.ema200 is not None and m.price > m.ema200


def _ema_stack_bullish(m: RecommendationInput) -> bool:
    if m.ema20 is None or m.ema50 is None or m.ema200 is None:
        return False
    return m.ema20 > m.ema50 > m.ema200


def _rsi_in_healthy_zone(m: RecommendationInput) -> bool:
    return m.rsi is not None and RSI_HEALTHY_MIN <= m.rsi <= RSI_HEALTHY_MAX


def _room_to_resistance(m: RecommendationInput) -> bool:
    headroom = m.headroom_pct
    return headroom is not None and headroom >= MIN_HEADROOM_PCT


def _clear_of_support(m: RecommendationInput) -> bool:
    cushion = m.support_cushion_pct
    return cushion is not None and cushion >= MIN_SUPPORT_CUSHION_PCT


# ---------- RSI zones ----------

RSI_HEALTHY_MIN: float = 55.0
RSI_HEALTHY_MAX: float = 70.0
RSI_OVERBOUGHT: float = 80.0
RSI_OVERSOLD: float = 30.0


# ---------- Level geometry (percentages of last price) ----------

# Minimum distance to resistance for a fresh entry; below it the setup is a
# breakout candidate rather than a buy.
MIN_HEADROOM_PCT: float = 2.0
# Minimum distance above support before a long is considered "clear" of it.
MIN_SUPPORT_CUSHION_PCT: float = 1.0
# Stop placed just under support, and never further away than the hard cap.
STOP_BUFFER_PCT: float = 0.5
MAX_STOP_DISTANCE_PCT: float = 5.0
# Second target extends the first target's move by this multiple.
SECOND_TARGET_EXTENSION: float = 1.5
# Setups whose reward:risk is below this are downgraded to "Watch".
MIN_RISK_REWARD: float = 1.2


SCORING_RULES: list[Rule] = [
    Rule("price_above_ema20", "Price above EMA20", 15, _price_above_ema20),
    Rule("price_above_ema50", "Price above EMA50", 10, _price_above_ema50),
    Rule("price_above_ema200", "Price above EMA200", 15, _price_above_ema200),
    Rule("ema_stack_bullish", "EMA20 > EMA50 > EMA200", 20, _ema_stack_bullish),
    Rule("rsi_healthy", "RSI in 55-70 zone", 15, _rsi_in_healthy_zone),
    Rule("room_to_resistance", "At least 2% room to resistance", 15, _room_to_resistance),
    Rule("clear_of_support", "At least 1% above support", 10, _clear_of_support),
]

MAX_SCORE: int = sum(rule.points for rule in SCORING_RULES)  # 100


# ---------- Conviction bands (inclusive lower bound) ----------

CONVICTION_BANDS: list[dict] = [
    {"min": 80, "label": "High"},
    {"min": 60, "label": "Medium"},
    {"min": 0, "label": "Low"},
]


# ---------- Action thresholds ----------

ACTION_BUY_MIN_SCORE: int = 80
ACTION_WATCH_MIN_SCORE: int = 60
ACTION_WAIT_MIN_SCORE: int = 40

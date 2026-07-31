"""Configuration for the TradeLens rule-based scoring engine.

Rules are declarative so they can be tuned or extended without touching the
service code. Each rule contributes points if its ``check`` returns True.
Maximum possible score across all rules should equal 100.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass(frozen=True)
class Rule:
    key: str
    label: str
    points: int
    check: Callable[[Dict], bool]


def _price_above_ema20(m: Dict) -> bool:
    return m["price"] > m["ema20"]


def _price_above_vwap(m: Dict) -> bool:
    return m["price"] > m["vwap"]


def _rsi_in_healthy_zone(m: Dict) -> bool:
    return 55.0 <= m["rsi"] <= 70.0


def _volume_above_average(m: Dict) -> bool:
    return m["volume"] > m["avg_volume"]


def _near_day_high(m: Dict) -> bool:
    return m["price"] >= m["day_high"] * 0.99


SCORING_RULES: List[Rule] = [
    Rule("above_ema20", "Price above EMA20", 20, _price_above_ema20),
    Rule("above_vwap", "Price above VWAP", 20, _price_above_vwap),
    Rule("rsi_healthy", "RSI in 55-70 zone", 15, _rsi_in_healthy_zone),
    Rule("volume_above_avg", "Volume above average", 25, _volume_above_average),
    Rule("near_day_high", "Price within 1% of Day High", 20, _near_day_high),
]

MAX_SCORE: int = sum(r.points for r in SCORING_RULES)  # 100

# Classification thresholds — inclusive lower bound.
CLASSIFICATIONS: List[Dict] = [
    {"min": 90, "stars": 5, "label": "Excellent"},
    {"min": 80, "stars": 4, "label": "Strong Watch"},
    {"min": 60, "stars": 3, "label": "Watch"},
    {"min": 0,  "stars": 2, "label": "Ignore"},
]


# Risk thresholds
RISK_LOW_MIN_SCORE = 85
RISK_MEDIUM_MIN_SCORE = 60


# Suggested action thresholds
ACTION_BUY_MIN_SCORE = 85
ACTION_WATCH_MIN_SCORE = 70
ACTION_WAIT_MIN_SCORE = 55

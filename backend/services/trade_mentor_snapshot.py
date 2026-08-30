"""Capture immutable Mentor recommendation snapshots at trade entry time."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.market_data_service import market_data_service
from services.stock_decision import decide

logger = logging.getLogger("tradelens.trade_mentor_snapshot")


def _first_reason(why: list[str], summary: str) -> Optional[str]:
    if why:
        return why[0]
    if summary and summary.strip():
        return summary.strip()
    return None


def build_mentor_snapshot(
    symbol: str,
    *,
    actual_entry_price: float,
    captured_at: datetime | None = None,
) -> Optional[Dict[str, Any]]:
    """Build a structured Mentor snapshot for one symbol at trade creation time.

    Uses the same stock + insight + ``decide()`` pipeline as ``GET /api/stock/{symbol}``.
    Does not trigger opportunity-universe evaluation.
    """
    normalized = symbol.strip().upper()
    stock = market_data_service.get_stock(normalized).data
    if not stock:
        logger.warning("trade_mentor_snapshot.missing_stock symbol=%s", normalized)
        return None

    insight = market_data_service.get_stock_insight(normalized).data or {}
    decision = decide(stock, insight)
    recommendation = decision.recommendation
    if recommendation is None:
        logger.info(
            "trade_mentor_snapshot.no_recommendation symbol=%s",
            normalized,
        )
        return {
            "action": None,
            "strategy": None,
            "entry_range_low": None,
            "entry_range_high": None,
            "actual_entry_price": actual_entry_price,
            "planned_stop_loss": None,
            "target_1": None,
            "target_2": None,
            "risk_reward": None,
            "holding_period": None,
            "reason": None,
            "captured_at": (captured_at or datetime.now(timezone.utc)).isoformat(),
        }

    levels = recommendation.levels
    snapshot: Dict[str, Any] = {
        "action": recommendation.action,
        "strategy": recommendation.strategy,
        "entry_range_low": levels.entry_min if levels else None,
        "entry_range_high": levels.entry_max if levels else None,
        "actual_entry_price": actual_entry_price,
        "planned_stop_loss": levels.stop_loss if levels else None,
        "target_1": levels.target1 if levels else None,
        "target_2": levels.target2 if levels else None,
        "risk_reward": levels.risk_reward if levels else None,
        "holding_period": recommendation.holding_period or None,
        "reason": _first_reason(recommendation.why, recommendation.summary),
        "captured_at": (captured_at or datetime.now(timezone.utc)).isoformat(),
    }
    logger.info(
        "trade_mentor_snapshot.captured symbol=%s action=%s strategy=%s",
        normalized,
        snapshot["action"],
        snapshot["strategy"],
    )
    return snapshot


def serialize_mentor_snapshot(snapshot: Optional[Dict[str, Any]]) -> Optional[str]:
    if snapshot is None:
        return None
    return json.dumps(snapshot)


def deserialize_mentor_snapshot(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("trade_mentor_snapshot.invalid_json")
        return None
    if not isinstance(payload, dict):
        return None
    return payload

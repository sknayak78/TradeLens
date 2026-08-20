"""Tests for ER-0028 UX polish — trade update validation."""
from __future__ import annotations

from datetime import datetime, timezone

from routers.trades import _calc_realized_pnl, _validate_trade_payload
from schemas import TradeUpdate


def test_trade_update_open_trade_validation():
    payload = TradeUpdate(
        trade_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        symbol="RELIANCE",
        side="LONG",
        entry_price=2500.0,
        quantity=10,
        notes="open position",
    )
    symbol, status = _validate_trade_payload(payload)
    assert symbol == "RELIANCE"
    assert status == "OPEN"


def test_trade_update_closed_trade_validation():
    payload = TradeUpdate(
        trade_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        symbol="RELIANCE",
        side="LONG",
        entry_price=2500.0,
        exit_price=2600.0,
        exit_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        quantity=10,
        notes="closed",
        confirm_out_of_range=True,
    )
    symbol, status = _validate_trade_payload(payload)
    assert symbol == "RELIANCE"
    assert status == "CLOSED"


def test_edited_closed_trade_pnl_recalculated():
    """Editing entry/exit should produce correct realized P&L."""
    pnl = _calc_realized_pnl("LONG", 2550.0, 2600.0, 15)
    assert pnl == 750.0

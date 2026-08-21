"""ER-0030 — open/closed trade lifecycle and quantity integrity tests."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db, init_db
from models import Trade
from server import app


def _buy_recommendation() -> SimpleNamespace:
    levels = SimpleNamespace(
        entry_min=1942.0,
        entry_max=1946.0,
        stop_loss=1871.10,
        target1=2031.0,
        target2=2101.0,
        risk_reward=1.14,
    )
    return SimpleNamespace(
        action="Buy",
        strategy="Pullback",
        holding_period="1-3 Weeks",
        why=["Healthy trend with pullback into preferred entry zone."],
        summary="Pullback setup in an uptrend.",
        levels=levels,
    )


def _decision():
    rec = _buy_recommendation()
    return SimpleNamespace(recommendation=rec, trend="bullish", score=78)


@pytest.fixture
def lifecycle_client(tmp_path, monkeypatch):
    db_path = tmp_path / "lifecycle.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    init_db(engine)
    app.dependency_overrides[get_db] = override_get_db

    stock = {
        "symbol": "RELIANCE",
        "name": "Reliance",
        "price": 1320.0,
        "changePct": 0.5,
        "rsi": 58.0,
        "ema20": 1300.0,
        "ema50": 1280.0,
        "ema200": 1200.0,
        "vwap": 1315.0,
        "volume": 1_000_000,
        "sector": "Energy",
    }

    def _stock_result(symbol: str):
        result = MagicMock()
        result.data = stock if symbol.upper() == "RELIANCE" else None
        return result

    monkeypatch.setattr(
        "routers.trades.market_data_service.get_stock",
        _stock_result,
    )
    monkeypatch.setattr(
        "routers.trades.market_data_service.search_stocks",
        lambda query, limit=20: MagicMock(
            data=[stock] if "RELIANCE" in query.upper() else []
        ),
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock",
        _stock_result,
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock_insight",
        lambda symbol: MagicMock(data={"support": 1200.0, "resistance": 1400.0, "series": []}),
    )
    monkeypatch.setattr(
        "routers.trades.get_day_ohlc_range",
        lambda *args, **kwargs: {"available": False},
    )
    monkeypatch.setattr("services.trade_mentor_snapshot.decide", lambda *a, **k: _decision())

    client = TestClient(app)
    yield client, TestingSessionLocal
    app.dependency_overrides.clear()
    engine.dispose()


def _create_open(client: TestClient, **overrides) -> dict:
    payload = {
        "symbol": "RELIANCE",
        "trade_date": "2026-08-21T09:30:00+00:00",
        "side": "LONG",
        "entry_price": 1316.0,
        "quantity": 4,
        "notes": "",
    }
    payload.update(overrides)
    response = client.post("/api/trades", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_open_trade_has_null_exit_fields(lifecycle_client):
    client, session_factory = lifecycle_client
    trade = _create_open(client)
    assert trade["status"] == "OPEN"
    assert trade["exit_price"] is None
    assert trade["exit_date"] is None
    assert trade["current_price"] == pytest.approx(1320.0)
    assert trade["unrealized_pnl"] == pytest.approx((1320.0 - 1316.0) * 4)

    with session_factory() as db:
        row = db.get(Trade, trade["id"])
        assert row is not None
        assert row.exit_price is None
        assert row.exit_date is None
        assert row.status == "OPEN"


def test_open_trade_does_not_store_market_price_as_exit_price(lifecycle_client):
    client, session_factory = lifecycle_client
    trade = _create_open(client, quantity=7)
    assert trade["exit_price"] is None

    with session_factory() as db:
        row = db.get(Trade, trade["id"])
        assert row.exit_price is None


def test_quantity_preserved_end_to_end(lifecycle_client):
    """Trace qty=7 from POST through DB to GET."""
    client, session_factory = lifecycle_client
    created = _create_open(client, quantity=7)
    assert created["quantity"] == 7

    with session_factory() as db:
        row = db.get(Trade, created["id"])
        assert row.quantity == 7

    fetched = client.get("/api/trades").json()
    match = next(row for row in fetched if row["id"] == created["id"])
    assert match["quantity"] == 7


def test_close_open_trade_via_edit(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client)
    original_snapshot = trade["mentor_snapshot"]

    closed = client.put(
        f"/api/trades/{trade['id']}",
        json={
            "status": "CLOSED",
            "exit_date": "2026-08-25T00:00:00+00:00",
            "exit_price": 1365.0,
        },
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "CLOSED"
    assert body["exit_price"] == pytest.approx(1365.0)
    assert body["exit_date"] is not None
    assert body["pnl"] == pytest.approx((1365.0 - 1316.0) * 4)
    assert body["unrealized_pnl"] is None
    assert body["mentor_snapshot"]["action"] == original_snapshot["action"]


def test_cannot_close_without_exit_details(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client)
    response = client.put(
        f"/api/trades/{trade['id']}",
        json={"status": "CLOSED"},
    )
    assert response.status_code == 400
    assert "exit date and exit price" in response.json()["detail"].lower()


def test_editing_quantity_preserves_mentor_snapshot(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client, quantity=4)
    original_action = trade["mentor_snapshot"]["action"]

    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"quantity": 7},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["quantity"] == 7
    assert body["mentor_snapshot"]["action"] == original_action


def test_reopen_trade_clears_exit_fields(lifecycle_client):
    client, session_factory = lifecycle_client
    trade = _create_open(client)
    client.put(
        f"/api/trades/{trade['id']}",
        json={
            "status": "CLOSED",
            "exit_date": "2026-08-25T00:00:00+00:00",
            "exit_price": 1365.0,
        },
    )

    reopened = client.put(
        f"/api/trades/{trade['id']}",
        json={"status": "OPEN"},
    )
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["status"] == "OPEN"
    assert body["exit_price"] is None
    assert body["exit_date"] is None

    with session_factory() as db:
        row = db.get(Trade, trade["id"])
        assert row.exit_price is None
        assert row.exit_date is None


def test_delete_then_recreate_quantity_integrity(lifecycle_client):
    client, _ = lifecycle_client
    first = _create_open(client, quantity=7, notes="first")
    assert client.delete(f"/api/trades/{first['id']}").status_code == 204

    second = _create_open(client, quantity=7, notes="second")
    listed = client.get("/api/trades").json()
    reliance = [row for row in listed if row["symbol"] == "RELIANCE"]
    assert len(reliance) == 1
    assert reliance[0]["quantity"] == 7
    assert reliance[0]["notes"] == "second"


def test_delete_one_of_two_same_symbol_trades(lifecycle_client):
    client, _ = lifecycle_client
    trade_a = _create_open(client, quantity=4, notes="A")
    trade_b = _create_open(client, quantity=2, notes="B")

    assert client.delete(f"/api/trades/{trade_a['id']}").status_code == 204

    listed = client.get("/api/trades").json()
    assert len(listed) == 1
    assert listed[0]["id"] == trade_b["id"]
    assert listed[0]["quantity"] == 2


def test_open_trade_remains_null_after_repeated_get(lifecycle_client):
    client, session_factory = lifecycle_client
    trade = _create_open(client)

    for _ in range(3):
        fetched = client.get("/api/trades").json()
        row = next(item for item in fetched if item["id"] == trade["id"])
        assert row["status"] == "OPEN"
        assert row["exit_price"] is None
        assert row["exit_date"] is None
        assert row["current_price"] == pytest.approx(1320.0)

    with session_factory() as db:
        row = db.get(Trade, trade["id"])
        assert row.exit_price is None
        assert row.exit_date is None


def test_closed_trade_edit_preserves_exit_fields(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client, notes="keep note")
    client.put(
        f"/api/trades/{trade['id']}",
        json={
            "status": "CLOSED",
            "exit_date": "2026-08-25T00:00:00+00:00",
            "exit_price": 1365.0,
        },
    )

    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"quantity": 5},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["status"] == "CLOSED"
    assert body["exit_price"] == pytest.approx(1365.0)
    assert body["exit_date"] is not None
    assert body["notes"] == "keep note"


def test_invalid_exit_price_rejected(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client)
    response = client.put(
        f"/api/trades/{trade['id']}",
        json={
            "status": "CLOSED",
            "exit_date": "2026-08-25T00:00:00+00:00",
            "exit_price": 0,
        },
    )
    assert response.status_code == 422


def test_exit_date_before_entry_rejected(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client)
    response = client.put(
        f"/api/trades/{trade['id']}",
        json={
            "status": "CLOSED",
            "exit_date": "2026-08-20T00:00:00+00:00",
            "exit_price": 1365.0,
        },
    )
    assert response.status_code == 400
    assert "before entry" in response.json()["detail"].lower()


def test_notes_unchanged_when_omitted_from_update(lifecycle_client):
    client, _ = lifecycle_client
    trade = _create_open(client, notes="original note")
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"quantity": 6},
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "original note"


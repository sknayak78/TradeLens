"""ER-0030 — automatic trade thesis / mentor snapshot regression tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from database import Base, get_db, init_db
from models import Trade
from server import app
from services.trade_mentor_snapshot import build_mentor_snapshot


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


def _watch_recommendation() -> SimpleNamespace:
    return SimpleNamespace(
        action="Watch",
        strategy="Consolidation",
        holding_period="1-2 Weeks",
        why=["Momentum has cooled after the morning move."],
        summary="Wait for a clearer setup.",
        levels=None,
    )


def _decision_from_recommendation(recommendation: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        recommendation=recommendation,
        trend="bullish",
        score=78,
    )


@pytest.fixture
def trade_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "er0030.db"
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
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel",
        "price": 1943.40,
        "changePct": 0.5,
        "rsi": 58.0,
        "ema20": 1930.0,
        "ema50": 1900.0,
        "ema200": 1850.0,
        "vwap": 1940.0,
        "volume": 1_000_000,
        "sector": "Telecom",
    }

    def _stock_result(symbol: str):
        result = MagicMock()
        result.data = stock if symbol.upper() == "BHARTIARTL" else None
        return result

    def _search_stocks(query: str, limit: int = 20):
        result = MagicMock()
        result.data = [stock] if "BHARTI" in query.upper() else []
        return result

    monkeypatch.setattr(
        "routers.trades.market_data_service.get_stock",
        _stock_result,
    )
    monkeypatch.setattr(
        "routers.trades.market_data_service.search_stocks",
        _search_stocks,
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock",
        _stock_result,
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock_insight",
        lambda symbol: MagicMock(data={"support": 1850.0, "resistance": 2100.0, "series": []}),
    )
    monkeypatch.setattr(
        "routers.trades.get_day_ohlc_range",
        lambda *args, **kwargs: {"available": False},
    )

    current_recommendation = {"value": _buy_recommendation()}

    def _decide(snapshot, insight=None):
        return _decision_from_recommendation(current_recommendation["value"])

    monkeypatch.setattr("services.trade_mentor_snapshot.decide", _decide)

    client = TestClient(app)
    yield client, TestingSessionLocal, current_recommendation
    app.dependency_overrides.clear()
    engine.dispose()


def _create_trade(client: TestClient, **overrides) -> dict:
    payload = {
        "symbol": "BHARTIARTL",
        "trade_date": "2026-08-21T09:30:00+00:00",
        "side": "LONG",
        "entry_price": 1943.40,
        "quantity": 10,
        "notes": "Entered based on morning recommendation.",
    }
    payload.update(overrides)
    response = client.post("/api/trades", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_trade_captures_mentor_snapshot(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    snapshot = trade["mentor_snapshot"]
    assert snapshot is not None
    assert snapshot["action"] == "Buy"


def test_buy_recommendation_stored_as_buy(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["action"] == "Buy"
    assert trade["mentor_snapshot"]["action"] != "Watch"


def test_strategy_is_captured(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["strategy"] == "Pullback"


def test_entry_range_is_captured(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    snapshot = trade["mentor_snapshot"]
    assert snapshot["entry_range_low"] == pytest.approx(1942.0)
    assert snapshot["entry_range_high"] == pytest.approx(1946.0)


def test_planned_stop_is_captured(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["planned_stop_loss"] == pytest.approx(1871.10)


def test_targets_are_captured(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    snapshot = trade["mentor_snapshot"]
    assert snapshot["target_1"] == pytest.approx(2031.0)
    assert snapshot["target_2"] == pytest.approx(2101.0)


def test_risk_reward_is_captured_when_available(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["risk_reward"] == pytest.approx(1.14)


def test_mentor_reason_is_captured_when_available(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert "pullback" in trade["mentor_snapshot"]["reason"].lower()


def test_snapshot_timestamp_is_captured(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["captured_at"] is not None


def test_editing_trade_does_not_change_mentor_snapshot(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    original_snapshot = trade["mentor_snapshot"]

    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"entry_price": 1945.0, "notes": "Adjusted fill price"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["entry_price"] == pytest.approx(1945.0)
    assert body["notes"] == "Adjusted fill price"
    assert body["mentor_snapshot"]["action"] == original_snapshot["action"]
    assert body["mentor_snapshot"]["entry_range_low"] == original_snapshot["entry_range_low"]
    assert body["mentor_snapshot"]["planned_stop_loss"] == original_snapshot["planned_stop_loss"]


def test_closing_trade_does_not_change_mentor_snapshot(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    original_action = trade["mentor_snapshot"]["action"]

    closed = client.put(
        f"/api/trades/{trade['id']}",
        json={
            "exit_date": "2026-08-28T00:00:00+00:00",
            "exit_price": 1980.0,
        },
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "CLOSED"
    assert body["mentor_snapshot"]["action"] == original_action


def test_existing_trades_without_snapshots_still_load(trade_client):
    client, session_factory, _ = trade_client
    with session_factory() as db:
        legacy = Trade(
            trade_date=datetime(2026, 1, 10, tzinfo=timezone.utc),
            symbol="BHARTIARTL",
            entry_price=1800.0,
            exit_price=1850.0,
            exit_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
            quantity=5,
            notes="legacy trade",
            side="LONG",
            status="CLOSED",
            mentor_snapshot=None,
        )
        db.add(legacy)
        db.commit()

    listed = client.get("/api/trades").json()
    legacy_row = next(row for row in listed if row["notes"] == "legacy trade")
    assert legacy_row["mentor_snapshot"] is None


def test_user_notes_remain_independent_and_editable(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client, notes="My own note")
    assert trade["notes"] == "My own note"

    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"notes": "Updated note only"},
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Updated note only"
    assert updated.json()["mentor_snapshot"]["action"] == "Buy"


def test_later_mentor_change_does_not_modify_historical_snapshot(trade_client):
    """Critical Bharti Airtel regression: BUY at entry must stay BUY after Mentor -> WATCH."""
    client, _, current_recommendation = trade_client
    trade = _create_trade(client)
    assert trade["mentor_snapshot"]["action"] == "Buy"

    current_recommendation["value"] = _watch_recommendation()

    fetched = client.get("/api/trades").json()
    saved = next(row for row in fetched if row["id"] == trade["id"])
    assert saved["mentor_snapshot"]["action"] == "Buy"
    assert saved["mentor_snapshot"]["action"] != "Watch"


def test_snapshot_creation_does_not_trigger_opportunity_universe(monkeypatch):
    called = {"select_opportunities": False}

    def _blocked_select(*args, **kwargs):
        called["select_opportunities"] = True
        raise AssertionError("select_opportunities must not run during trade snapshot capture")

    monkeypatch.setattr(
        "services.opportunity_selection.select_opportunities",
        _blocked_select,
    )

    stock = {
        "symbol": "RELIANCE",
        "name": "Reliance",
        "price": 2500.0,
        "changePct": 0.2,
        "rsi": 55.0,
        "ema20": 2480.0,
        "ema50": 2450.0,
        "ema200": 2400.0,
        "vwap": 2490.0,
        "volume": 1_000_000,
        "sector": "Energy",
    }
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock",
        lambda symbol: MagicMock(data=stock),
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.market_data_service.get_stock_insight",
        lambda symbol: MagicMock(data={"support": 2400.0, "resistance": 2600.0, "series": []}),
    )
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.decide",
        lambda snapshot, insight=None: _decision_from_recommendation(_buy_recommendation()),
    )

    snapshot = build_mentor_snapshot("RELIANCE", actual_entry_price=2500.0)
    assert snapshot is not None
    assert snapshot["action"] == "Buy"
    assert called["select_opportunities"] is False


def test_mentor_snapshot_migration_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "mentor-snapshot-migration.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATETIME NOT NULL,
                    symbol VARCHAR(32) NOT NULL,
                    entry_price FLOAT NOT NULL,
                    exit_price FLOAT,
                    quantity INTEGER NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    side VARCHAR(8) NOT NULL DEFAULT 'LONG',
                    exit_date DATETIME,
                    status VARCHAR(8) NOT NULL DEFAULT 'CLOSED'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO trades (
                    trade_date, symbol, entry_price, exit_price, quantity, notes, side, status
                ) VALUES (
                    '2026-01-15 00:00:00', 'RELIANCE', 100.0, 110.0, 10, 'pre-er0030', 'LONG', 'CLOSED'
                )
                """
            )
        )

    init_db(engine)
    init_db(engine)

    columns = {col["name"] for col in inspect(engine).get_columns("trades")}
    assert "mentor_snapshot" in columns

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT notes, mentor_snapshot FROM trades WHERE symbol = 'RELIANCE'")
        ).mappings().one()
    assert row["notes"] == "pre-er0030"
    assert row["mentor_snapshot"] is None
    engine.dispose()


def test_snapshot_round_trip_json_shape(trade_client):
    client, session_factory, _ = trade_client
    trade = _create_trade(client)
    with session_factory() as db:
        stored = db.get(Trade, trade["id"])
        assert stored is not None
        payload = json.loads(stored.mentor_snapshot)
        assert payload["action"] == "Buy"
        assert payload["actual_entry_price"] == pytest.approx(1943.40)


def test_delete_then_recreate_reliance_leaves_one_trade(trade_client):
    """Delete → create must not leave the deleted trade in the journal."""
    client, session_factory, _ = trade_client
    created = _create_trade(client)
    trade_id = created["id"]

    deleted = client.delete(f"/api/trades/{trade_id}")
    assert deleted.status_code == 204

    with session_factory() as db:
        assert db.get(Trade, trade_id) is None

    recreated = _create_trade(client, notes="recreated reliance")
    listed = client.get("/api/trades").json()
    reliance_rows = [row for row in listed if row["symbol"] == "BHARTIARTL"]

    assert len(reliance_rows) == 1
    assert reliance_rows[0]["id"] == recreated["id"]
    assert reliance_rows[0]["notes"] == "recreated reliance"


def test_multiple_intentional_same_symbol_trades_are_allowed(trade_client):
    client, _, _ = trade_client
    first = _create_trade(client, quantity=100, notes="trade A")
    second = _create_trade(client, quantity=50, notes="trade B")

    listed = client.get("/api/trades").json()
    reliance_rows = [row for row in listed if row["symbol"] == "BHARTIARTL"]

    assert len(reliance_rows) == 2
    ids = {row["id"] for row in reliance_rows}
    assert ids == {first["id"], second["id"]}


def test_updating_note_does_not_modify_mentor_snapshot(trade_client):
    client, _, _ = trade_client
    trade = _create_trade(client)
    original_snapshot = trade["mentor_snapshot"]

    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"notes": "My personal reflection on this trade."},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["notes"] == "My personal reflection on this trade."
    assert body["mentor_snapshot"]["action"] == original_snapshot["action"]
    assert body["mentor_snapshot"]["strategy"] == original_snapshot["strategy"]

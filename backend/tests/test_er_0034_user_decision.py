"""ER-0034 — structured user decision/thesis/invalidation capture tests.

The user's own decision, thesis and invalidation are stored separately from the
Mentor recommendation snapshot. Update paths must never modify mentor_snapshot.
"""
from __future__ import annotations

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


@pytest.fixture
def trade_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "er0034.db"
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
    monkeypatch.setattr(
        "services.trade_mentor_snapshot.decide",
        lambda snapshot, insight=None: SimpleNamespace(
            recommendation=_buy_recommendation(),
            trend="bullish",
            score=78,
        ),
    )

    client = TestClient(app)
    yield client, TestingSessionLocal
    app.dependency_overrides.clear()
    engine.dispose()


def _create_trade(client: TestClient, **overrides) -> dict:
    payload = {
        "symbol": "BHARTIARTL",
        "trade_date": "2026-08-21T09:30:00+00:00",
        "side": "LONG",
        "entry_price": 1943.40,
        "quantity": 10,
        "notes": "note text",
    }
    payload.update(overrides)
    response = client.post("/api/trades", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_trade_persists_all_three_fields(trade_client):
    client, _ = trade_client
    trade = _create_trade(
        client,
        user_decision="BUY",
        user_thesis="Momentum should continue higher.",
        user_invalidation="A close below 1871 breaks the thesis.",
    )
    assert trade["user_decision"] == "BUY"
    assert trade["user_thesis"] == "Momentum should continue higher."
    assert trade["user_invalidation"] == "A close below 1871 breaks the thesis."


def test_update_all_three_fields_persists_changes(trade_client):
    client, _ = trade_client
    trade = _create_trade(client, user_decision="WATCH")
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={
            "user_decision": "SELL",
            "user_thesis": "Reversal confirmed.",
            "user_invalidation": "A higher high invalidates.",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["user_decision"] == "SELL"
    assert body["user_thesis"] == "Reversal confirmed."
    assert body["user_invalidation"] == "A higher high invalidates."


def test_updating_user_decision_does_not_change_mentor_snapshot(trade_client):
    client, _ = trade_client
    trade = _create_trade(client)
    original = trade["mentor_snapshot"]
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"user_decision": "BUY"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["user_decision"] == "BUY"
    assert body["mentor_snapshot"]["action"] == original["action"]
    assert body["mentor_snapshot"]["entry_range_low"] == original["entry_range_low"]
    assert body["mentor_snapshot"]["planned_stop_loss"] == original["planned_stop_loss"]


def test_updating_user_thesis_does_not_change_mentor_snapshot(trade_client):
    client, _ = trade_client
    trade = _create_trade(client)
    original = trade["mentor_snapshot"]
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"user_thesis": "New thesis text."},
    )
    assert updated.status_code == 200
    assert updated.json()["user_thesis"] == "New thesis text."
    assert updated.json()["mentor_snapshot"]["action"] == original["action"]


def test_updating_user_invalidation_does_not_change_mentor_snapshot(trade_client):
    client, _ = trade_client
    trade = _create_trade(client)
    original = trade["mentor_snapshot"]
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"user_invalidation": "New invalidation."},
    )
    assert updated.status_code == 200
    assert updated.json()["user_invalidation"] == "New invalidation."
    assert updated.json()["mentor_snapshot"]["action"] == original["action"]


def test_notes_and_new_fields_remain_independent(trade_client):
    client, _ = trade_client
    trade = _create_trade(
        client,
        notes="keep this note",
        user_decision="BUY",
        user_thesis="thesis text",
        user_invalidation="invalid text",
    )
    # Edit only the note; the three fields must persist unchanged.
    updated = client.put(
        f"/api/trades/{trade['id']}",
        json={"notes": "updated note only"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["notes"] == "updated note only"
    assert body["user_decision"] == "BUY"
    assert body["user_thesis"] == "thesis text"
    assert body["user_invalidation"] == "invalid text"

    # Edit only the user fields; the note must persist unchanged.
    updated2 = client.put(
        f"/api/trades/{trade['id']}",
        json={"user_decision": "AVOID"},
    )
    assert updated2.status_code == 200
    assert updated2.json()["notes"] == "updated note only"
    assert updated2.json()["user_decision"] == "AVOID"


def test_mentor_snapshot_migration_adds_all_three_columns(tmp_path: Path):
    db_path = tmp_path / "er0034-migration.db"
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
                    status VARCHAR(8) NOT NULL DEFAULT 'CLOSED',
                    mentor_snapshot TEXT
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
                    '2026-01-15 00:00:00', 'RELIANCE', 100.0, 110.0, 10, 'pre-er0034', 'LONG', 'CLOSED'
                )
                """
            )
        )

    init_db(engine)

    columns = {col["name"] for col in inspect(engine).get_columns("trades")}
    assert "user_decision" in columns
    assert "user_thesis" in columns
    assert "user_invalidation" in columns

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT notes, user_decision, user_thesis, user_invalidation "
                "FROM trades WHERE symbol = 'RELIANCE'"
            )
        ).mappings().one()
    assert row["notes"] == "pre-er0034"
    assert row["user_decision"] is None
    assert row["user_thesis"] is None
    assert row["user_invalidation"] is None
    engine.dispose()


def test_migration_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "er0034-idempotent.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    init_db(engine)
    init_db(engine)
    init_db(engine)
    columns = {col["name"] for col in inspect(engine).get_columns("trades")}
    assert "user_decision" in columns
    assert "user_thesis" in columns
    assert "user_invalidation" in columns
    engine.dispose()


def test_existing_trades_without_fields_still_load(trade_client):
    client, session_factory = trade_client
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
            user_decision=None,
            user_thesis=None,
            user_invalidation=None,
        )
        db.add(legacy)
        db.commit()

    listed = client.get("/api/trades").json()
    legacy_row = next(row for row in listed if row["notes"] == "legacy trade")
    assert legacy_row["user_decision"] is None
    assert legacy_row["user_thesis"] is None
    assert legacy_row["user_invalidation"] is None


def test_migration_against_prepopulated_temporary_db(tmp_path: Path):
    """A pre-existing DB (with data) gains the three columns without data loss."""
    db_path = tmp_path / "er0034-prepopulated.db"
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
                    status VARCHAR(8) NOT NULL DEFAULT 'CLOSED',
                    mentor_snapshot TEXT
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
                    '2026-03-01 00:00:00', 'TCS', 3500.0, 3520.0, 5, 'existing', 'LONG', 'CLOSED'
                )
                """
            )
        )

    init_db(engine)

    columns = {col["name"] for col in inspect(engine).get_columns("trades")}
    assert "user_decision" in columns
    assert "user_thesis" in columns
    assert "user_invalidation" in columns

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT symbol, notes FROM trades WHERE symbol = 'TCS'")
        ).mappings().one()
    assert row["symbol"] == "TCS"
    assert row["notes"] == "existing"
    engine.dispose()

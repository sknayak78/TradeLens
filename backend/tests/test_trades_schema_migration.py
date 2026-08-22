"""Regression tests for idempotent trades schema migration."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from database import _TRADES_NEW_TABLE, _TRADES_TABLE, init_db


def _legacy_trades_ddl() -> str:
    return f"""
        CREATE TABLE {_TRADES_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATETIME NOT NULL,
            symbol VARCHAR(32) NOT NULL,
            entry_price FLOAT NOT NULL,
            exit_price FLOAT NOT NULL,
            quantity INTEGER NOT NULL,
            notes TEXT NOT NULL DEFAULT ''
        )
    """


def _legacy_trades_with_partial_columns_ddl() -> str:
    return f"""
        CREATE TABLE {_TRADES_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATETIME NOT NULL,
            symbol VARCHAR(32) NOT NULL,
            entry_price FLOAT NOT NULL,
            exit_price FLOAT NOT NULL,
            quantity INTEGER NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            side VARCHAR(8) NOT NULL DEFAULT 'LONG',
            exit_date DATETIME,
            status VARCHAR(8) NOT NULL DEFAULT 'CLOSED'
        )
    """


def _new_trades_ddl() -> str:
    return f"""
        CREATE TABLE {_TRADES_NEW_TABLE} (
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


@pytest.fixture
def temp_engine(tmp_path: Path):
    db_path = tmp_path / "migration-test.db"
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    yield eng
    eng.dispose()


def _seed_legacy_trade(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(_legacy_trades_ddl()))
        connection.execute(
            text(
                f"""
                INSERT INTO {_TRADES_TABLE} (
                    trade_date, symbol, entry_price, exit_price, quantity, notes
                ) VALUES (
                    '2026-01-15 00:00:00', 'RELIANCE', 100.0, 110.0, 10, 'legacy trade'
                )
                """
            )
        )


def _exit_price_nullable(engine) -> bool:
    columns = inspect(engine).get_columns(_TRADES_TABLE)
    exit_price_col = next(col for col in columns if col["name"] == "exit_price")
    return bool(exit_price_col.get("nullable"))


def _trade_rows(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT id, symbol, entry_price, exit_price, side, exit_date, status, notes, mentor_snapshot
                FROM {_TRADES_TABLE}
                ORDER BY id
                """
            )
        ).mappings().all()
    return [dict(row) for row in rows]


def test_clean_migration_from_legacy_schema(temp_engine):
    _seed_legacy_trade(temp_engine)

    init_db(temp_engine)

    rows = _trade_rows(temp_engine)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["entry_price"] == 100.0
    assert rows[0]["exit_price"] == 110.0
    assert rows[0]["side"] == "LONG"
    assert rows[0]["status"] == "CLOSED"
    assert rows[0]["exit_date"] is None
    assert rows[0]["notes"] == "legacy trade"
    assert _exit_price_nullable(temp_engine)
    assert _TRADES_NEW_TABLE not in inspect(temp_engine).get_table_names()


def test_repeated_init_db_is_idempotent(temp_engine):
    _seed_legacy_trade(temp_engine)

    init_db(temp_engine)
    init_db(temp_engine)
    init_db(temp_engine)

    rows = _trade_rows(temp_engine)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert _exit_price_nullable(temp_engine)
    assert _TRADES_NEW_TABLE not in inspect(temp_engine).get_table_names()


def test_stale_trades_new_recovery_preserves_existing_trades(temp_engine):
    _seed_legacy_trade(temp_engine)
    with temp_engine.begin() as connection:
        connection.execute(text(_new_trades_ddl()))

    init_db(temp_engine)

    rows = _trade_rows(temp_engine)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["notes"] == "legacy trade"
    assert _exit_price_nullable(temp_engine)
    assert _TRADES_NEW_TABLE not in inspect(temp_engine).get_table_names()


def test_interrupted_migration_after_drop_trades_recovers(temp_engine):
    _seed_legacy_trade(temp_engine)
    with temp_engine.begin() as connection:
        connection.execute(text(_new_trades_ddl()))
        connection.execute(
            text(
                f"""
                INSERT INTO {_TRADES_NEW_TABLE} (
                    id, trade_date, symbol, entry_price, exit_price, quantity, notes, side, exit_date, status
                )
                SELECT
                    id, trade_date, symbol, entry_price, exit_price, quantity,
                    COALESCE(notes, ''), 'LONG', NULL, 'CLOSED'
                FROM {_TRADES_TABLE}
                """
            )
        )
        connection.execute(text(f"DROP TABLE {_TRADES_TABLE}"))

    init_db(temp_engine)

    rows = _trade_rows(temp_engine)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert _exit_price_nullable(temp_engine)


def test_migrated_schema_supports_nullable_exit_price_for_open_trades(temp_engine):
    _seed_legacy_trade(temp_engine)
    init_db(temp_engine)

    with temp_engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {_TRADES_TABLE} (
                    trade_date, symbol, entry_price, exit_price, quantity, notes, side, exit_date, status
                ) VALUES (
                    '2026-08-19 00:00:00', 'TCS', 3500.0, NULL, 5, 'open position', 'SHORT', NULL, 'OPEN'
                )
                """
            )
        )

    rows = _trade_rows(temp_engine)
    open_trade = next(row for row in rows if row["symbol"] == "TCS")
    assert open_trade["exit_price"] is None
    assert open_trade["side"] == "SHORT"
    assert open_trade["status"] == "OPEN"
    assert open_trade["exit_date"] is None


def test_partial_legacy_columns_are_migrated_with_defaults(temp_engine):
    with temp_engine.begin() as connection:
        connection.execute(text(_legacy_trades_with_partial_columns_ddl()))
        connection.execute(
            text(
                f"""
                INSERT INTO {_TRADES_TABLE} (
                    trade_date, symbol, entry_price, exit_price, quantity, notes, side, status
                ) VALUES (
                    '2026-02-01 00:00:00', 'INFY', 1500.0, 1525.0, 20, 'partial cols', 'SHORT', 'CLOSED'
                )
                """
            )
        )

    init_db(temp_engine)

    rows = _trade_rows(temp_engine)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "INFY"
    assert rows[0]["side"] == "SHORT"
    assert rows[0]["status"] == "CLOSED"
    assert _exit_price_nullable(temp_engine)

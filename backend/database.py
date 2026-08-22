"""SQLite database configuration for TradeLens."""
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "tradelens.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_TRADES_NEW_TABLE = "trades_new"
_TRADES_TABLE = "trades"


def _create_trades_new_table_sql() -> str:
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


def _trades_table_names(db_engine: Engine) -> set[str]:
    return set(inspect(db_engine).get_table_names())


def _trades_migration_complete(db_engine: Engine) -> bool:
    if _TRADES_TABLE not in _trades_table_names(db_engine):
        return False
    columns = inspect(db_engine).get_columns(_TRADES_TABLE)
    exit_price_col = next((col for col in columns if col["name"] == "exit_price"), None)
    return exit_price_col is not None and bool(exit_price_col.get("nullable"))


def _copy_trades_into_new_table_sql(column_names: set[str]) -> str:
    notes_expr = "COALESCE(notes, '')" if "notes" in column_names else "''"
    side_expr = "COALESCE(side, 'LONG')" if "side" in column_names else "'LONG'"
    exit_date_expr = "exit_date" if "exit_date" in column_names else "NULL"
    status_expr = "COALESCE(status, 'CLOSED')" if "status" in column_names else "'CLOSED'"
    return f"""
        INSERT INTO {_TRADES_NEW_TABLE} (
            id, trade_date, symbol, entry_price, exit_price, quantity, notes, side, exit_date, status
        )
        SELECT
            id,
            trade_date,
            symbol,
            entry_price,
            exit_price,
            quantity,
            {notes_expr},
            {side_expr},
            {exit_date_expr},
            {status_expr}
        FROM {_TRADES_TABLE}
    """


def _finalize_trades_rename(connection) -> None:
    connection.execute(text(f"ALTER TABLE {_TRADES_NEW_TABLE} RENAME TO {_TRADES_TABLE}"))
    connection.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_trades_symbol ON {_TRADES_TABLE} (symbol)")
    )


def _drop_stale_trades_new(connection) -> None:
    connection.execute(text(f"DROP TABLE IF EXISTS {_TRADES_NEW_TABLE}"))


def _recover_interrupted_trades_migration(db_engine: Engine) -> None:
    """Complete a migration interrupted after the legacy table was dropped."""
    table_names = _trades_table_names(db_engine)
    if _TRADES_TABLE in table_names or _TRADES_NEW_TABLE not in table_names:
        return
    with db_engine.begin() as connection:
        _finalize_trades_rename(connection)


def _migrate_trades_schema(db_engine: Engine | None = None) -> None:
    """Upgrade the trades table to the ER-0027 schema.

    Safe to call repeatedly. Recovers from interrupted migrations that leave
    behind a stale ``trades_new`` table or rename the temporary table when the
    legacy ``trades`` table was already dropped.
    """
    eng = db_engine or engine
    table_names = _trades_table_names(eng)

    if _trades_migration_complete(eng):
        if _TRADES_NEW_TABLE in table_names:
            with eng.begin() as connection:
                _drop_stale_trades_new(connection)
        _migrate_trades_mentor_snapshot(eng)
        return

    # Interrupted migration after DROP TABLE trades: complete the rename only.
    if _TRADES_TABLE not in table_names and _TRADES_NEW_TABLE in table_names:
        with eng.begin() as connection:
            _finalize_trades_rename(connection)
        _migrate_trades_mentor_snapshot(eng)
        return

    if _TRADES_TABLE not in table_names:
        return

    column_names = {col["name"] for col in inspect(eng).get_columns(_TRADES_TABLE)}

    with eng.begin() as connection:
        _drop_stale_trades_new(connection)
        connection.execute(text(_create_trades_new_table_sql()))
        connection.execute(text(_copy_trades_into_new_table_sql(column_names)))
        connection.execute(text(f"DROP TABLE {_TRADES_TABLE}"))
        _finalize_trades_rename(connection)

    _migrate_trades_mentor_snapshot(eng)


def _mentor_snapshot_column_present(db_engine: Engine) -> bool:
    if _TRADES_TABLE not in _trades_table_names(db_engine):
        return False
    columns = inspect(db_engine).get_columns(_TRADES_TABLE)
    return any(col["name"] == "mentor_snapshot" for col in columns)


def _migrate_trades_mentor_snapshot(db_engine: Engine | None = None) -> None:
    """Add the ER-0030 mentor_snapshot column when missing.

  Safe to call repeatedly; existing trades keep a NULL snapshot.
    """
    eng = db_engine or engine
    if _TRADES_TABLE not in _trades_table_names(eng):
        return
    if _mentor_snapshot_column_present(eng):
        return
    with eng.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE {_TRADES_TABLE} ADD COLUMN mentor_snapshot TEXT")
        )


def init_db(db_engine: Engine | None = None) -> None:
    """Create tables (if not already present)."""
    # Import models so metadata is populated
    import models  # noqa: F401

    eng = db_engine or engine
    _recover_interrupted_trades_migration(eng)
    Base.metadata.create_all(bind=eng)
    _migrate_trades_schema(eng)

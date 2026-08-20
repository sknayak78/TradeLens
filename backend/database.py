"""SQLite database configuration for TradeLens."""
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
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


def _migrate_trades_schema() -> None:
    """Add open/closed trade columns and nullable exit price without dropping rows."""
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("trades")
    exit_price_col = next((col for col in columns if col["name"] == "exit_price"), None)
    if exit_price_col is not None and exit_price_col.get("nullable"):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE trades_new (
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
                INSERT INTO trades_new (
                    id, trade_date, symbol, entry_price, exit_price, quantity, notes, side, exit_date, status
                )
                SELECT
                    id,
                    trade_date,
                    symbol,
                    entry_price,
                    exit_price,
                    quantity,
                    COALESCE(notes, ''),
                    COALESCE(side, 'LONG'),
                    exit_date,
                    COALESCE(status, 'CLOSED')
                FROM trades
                """
            )
        )
        connection.execute(text("DROP TABLE trades"))
        connection.execute(text("ALTER TABLE trades_new RENAME TO trades"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_trades_symbol ON trades (symbol)")
        )


def init_db() -> None:
    """Create tables (if not already present)."""
    # Import models so metadata is populated
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_trades_schema()

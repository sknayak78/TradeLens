"""TradeLens FastAPI application.

Lightweight server: FastAPI + SQLAlchemy + SQLite.
- Persists Watchlist, Trades and Settings in SQLite.
- Serves market summary / opportunities / stock detail from static seed data.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import select

from database import init_db, SessionLocal
from models import WatchlistItem
from seed_data import DEFAULT_WATCHLIST_SYMBOLS
from routers import watchlist as watchlist_router
from routers import trades as trades_router
from routers import settings as settings_router
from routers import market as market_router


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tradelens")


def _seed_default_watchlist() -> None:
    """On first run, seed the default watchlist so the UI has data immediately."""
    db = SessionLocal()
    try:
        existing_count = db.query(WatchlistItem).count()
        if existing_count > 0:
            return
        for sym in DEFAULT_WATCHLIST_SYMBOLS:
            db.add(WatchlistItem(symbol=sym))
        db.commit()
        logger.info("Seeded %d default watchlist symbols", len(DEFAULT_WATCHLIST_SYMBOLS))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_default_watchlist()
    logger.info("TradeLens ready")
    yield


app = FastAPI(title="TradeLens API", version="1.0.0", lifespan=lifespan)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
def root() -> dict:
    return {"service": "TradeLens", "status": "ok"}


@api_router.get("/health")
def health() -> dict:
    return {"status": "healthy"}


api_router.include_router(watchlist_router.router)
api_router.include_router(trades_router.router)
api_router.include_router(settings_router.router)
api_router.include_router(market_router.router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

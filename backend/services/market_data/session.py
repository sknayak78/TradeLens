"""Market session helpers shared by normalized providers."""
from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from services.market_data.models import MarketStatus, MarketStatusValue


def market_session_status(now: datetime | None = None) -> MarketStatusValue:
    """Return the NSE session bucket using the same IST rules as MarketDataService."""
    india_now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("Asia/Kolkata"))
    if india_now.weekday() >= 5:
        return "WEEKEND"
    current_time = india_now.time()
    if time(9, 0) <= current_time < time(9, 15):
        return "PRE_OPEN"
    if time(9, 15) <= current_time < time(15, 30):
        return "OPEN"
    return "CLOSED"


def current_market_status(now: datetime | None = None) -> MarketStatus:
    """Return a normalized market-status payload."""
    when = now or datetime.now(timezone.utc)
    return MarketStatus(status=market_session_status(when), as_of=when)

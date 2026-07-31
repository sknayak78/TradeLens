"""Market data endpoints — served from static seed data."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException

from schemas import (
    MarketSummary,
    IndexItem,
    TodaysFocusItem,
    Opportunity,
    StockDetail,
    StockSummary,
    SeriesPoint,
)
from seed_data import (
    MARKET_INDICES,
    TODAYS_FOCUS,
    OPPORTUNITIES,
    STOCKS_BY_SYMBOL,
    INSIGHTS,
    synthesize_insight,
)

router = APIRouter(tags=["market"])


@router.get("/stocks", response_model=List[StockSummary])
def list_stocks(q: str = "", limit: int = 20) -> List[StockSummary]:
    """Return the stock catalog. Optional `q` filters by symbol or name."""
    query = q.strip().lower()
    if query:
        matches = [
            s for s in STOCKS_BY_SYMBOL.values()
            if query in s["symbol"].lower() or query in s["name"].lower()
        ]
    else:
        matches = list(STOCKS_BY_SYMBOL.values())
    matches = matches[: max(1, min(limit, 100))]
    return [
        StockSummary(
            symbol=s["symbol"],
            name=s["name"],
            price=s["price"],
            changePct=s["changePct"],
            trend=s["trend"],
            sector=s["sector"],
        )
        for s in matches
    ]


@router.get("/market-summary", response_model=MarketSummary)
def market_summary() -> MarketSummary:
    return MarketSummary(
        indices=[IndexItem(**i) for i in MARKET_INDICES],
        todaysFocus=[TodaysFocusItem(**f) for f in TODAYS_FOCUS],
        status="open",
        asOf=datetime.now(timezone.utc),
    )


@router.get("/opportunities", response_model=List[Opportunity])
def opportunities() -> List[Opportunity]:
    out: List[Opportunity] = []
    for o in OPPORTUNITIES:
        stock = STOCKS_BY_SYMBOL.get(o["symbol"])
        if not stock:
            continue
        out.append(
            Opportunity(
                symbol=stock["symbol"],
                name=stock["name"],
                score=o["score"],
                trend=stock["trend"],
                price=stock["price"],
                changePct=stock["changePct"],
                reason=o["reason"],
            )
        )
    return out


@router.get("/stock/{symbol}", response_model=StockDetail)
def stock_detail(symbol: str) -> StockDetail:
    symbol = symbol.strip().upper()
    stock = STOCKS_BY_SYMBOL.get(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    insight = INSIGHTS.get(symbol) or synthesize_insight(symbol)
    return StockDetail(
        symbol=stock["symbol"],
        name=stock["name"],
        price=stock["price"],
        changePct=stock["changePct"],
        score=stock["score"],
        trend=stock["trend"],
        rsi=stock["rsi"],
        ema20=stock["ema20"],
        vwap=stock["vwap"],
        volume=stock["volume"],
        sector=stock["sector"],
        support=insight["support"],
        resistance=insight["resistance"],
        aiInsight=insight["aiInsight"],
        series=[SeriesPoint(**p) for p in insight["series"]],
    )

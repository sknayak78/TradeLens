"""Watchlist endpoints — persistent user watchlist joined with market data."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import WatchlistItem
from schemas import WatchlistCreate, WatchlistAnalysis
from analysis.service import service as analysis_service
from services.market_data_service import market_data_service
from services.stock_decision import decide

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _enrich(symbol: str) -> WatchlistAnalysis:
    result = market_data_service.get_stock(symbol)
    stock = result.data
    metadata = result.metadata.to_api_dict()
    if not stock:
        # Unknown symbol — return minimal placeholder row so UI doesn't break.
        return WatchlistAnalysis(
            **metadata,
            symbol=symbol,
            name=symbol,
            price=0.0,
            rsi=0.0,
            ema20=0.0,
            vwap=0.0,
            score=0,
            trend="neutral",
            changePct=0.0,
            strengthScore=0,
            stars=2,
            tradeSetup="Consolidation",
            riskLevel="High",
            suggestedAction="Avoid",
        )
    analysis = analysis_service.analyse(stock)
    decision = decide(stock)
    return WatchlistAnalysis(
        **metadata,
        symbol=stock["symbol"],
        name=stock["name"],
        price=stock["price"],
        rsi=stock["rsi"],
        ema20=stock["ema20"],
        vwap=stock["vwap"],
        # Parent trend/score are the recommendation's, never the provider's.
        score=decision.score,
        trend=decision.trend,
        changePct=stock["changePct"],
        strengthScore=analysis.strength_score,
        stars=analysis.stars,
        tradeSetup=analysis.trade_setup,
        riskLevel=analysis.risk_level,
        suggestedAction=analysis.suggested_action,
    )


@router.get("", response_model=List[WatchlistAnalysis])
def list_watchlist(db: Session = Depends(get_db)) -> List[WatchlistAnalysis]:
    rows = db.scalars(select(WatchlistItem).order_by(WatchlistItem.created_at.asc())).all()
    return [_enrich(r.symbol) for r in rows]


@router.post("", response_model=WatchlistAnalysis, status_code=status.HTTP_201_CREATED)
def add_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)) -> WatchlistAnalysis:
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    existing = db.scalar(select(WatchlistItem).where(WatchlistItem.symbol == symbol))
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} already in watchlist")

    item = WatchlistItem(symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _enrich(item.symbol)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(symbol: str, db: Session = Depends(get_db)) -> None:
    symbol = symbol.strip().upper()
    item = db.scalar(select(WatchlistItem).where(WatchlistItem.symbol == symbol))
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    db.delete(item)
    db.commit()
    return None

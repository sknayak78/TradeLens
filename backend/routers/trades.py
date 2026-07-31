"""Trade log endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import Trade
from schemas import TradeCreate, TradeOut

router = APIRouter(prefix="/trades", tags=["trades"])


def _to_out(t: Trade) -> TradeOut:
    # If exit >= entry, treat as LONG (buy then sell higher).
    # Otherwise treat as SHORT (sell high, buy back lower is a profit).
    if t.exit_price >= t.entry_price:
        side = "LONG"
        pnl = round((t.exit_price - t.entry_price) * t.quantity, 2)
    else:
        side = "SHORT"
        pnl = round((t.entry_price - t.exit_price) * t.quantity, 2)
    return TradeOut(
        id=t.id,
        trade_date=t.trade_date,
        symbol=t.symbol,
        entry_price=t.entry_price,
        exit_price=t.exit_price,
        quantity=t.quantity,
        notes=t.notes,
        pnl=pnl,
        side=side,
    )


@router.get("", response_model=List[TradeOut])
def list_trades(db: Session = Depends(get_db)) -> List[TradeOut]:
    rows = db.scalars(select(Trade).order_by(Trade.trade_date.desc(), Trade.id.desc())).all()
    return [_to_out(t) for t in rows]


@router.post("", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)) -> TradeOut:
    trade = Trade(
        trade_date=payload.trade_date,
        symbol=payload.symbol.strip().upper(),
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
        quantity=payload.quantity,
        notes=payload.notes or "",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return _to_out(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(trade_id: int, db: Session = Depends(get_db)) -> None:
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    db.delete(trade)
    db.commit()
    return None

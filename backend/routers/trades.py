"""Trade log endpoints."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Trade
from schemas import TradeCreate, TradeOut
from services.chart_series import get_day_ohlc_range
from services.market_data_service import market_data_service

router = APIRouter(prefix="/trades", tags=["trades"])


def _as_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(timezone.utc).date()


def _calc_realized_pnl(side: str, entry: float, exit_price: float, quantity: int) -> float:
    if side == "SHORT":
        return round((entry - exit_price) * quantity, 2)
    return round((exit_price - entry) * quantity, 2)


def _calc_unrealized_pnl(side: str, entry: float, current: float, quantity: int) -> float:
    if side == "SHORT":
        return round((entry - current) * quantity, 2)
    return round((current - entry) * quantity, 2)


def _holding_period_days(entry: datetime, exit_dt: datetime) -> int:
    return max((_as_date(exit_dt) - _as_date(entry)).days, 0)


def _current_price(symbol: str) -> float | None:
    stock = market_data_service.get_stock(symbol).data
    if not stock:
        return None
    return float(stock["price"])


def _validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    matches = market_data_service.search_stocks(normalized, limit=1).data
    if not matches:
        raise HTTPException(
            status_code=400,
            detail="Please select a valid stock symbol.",
        )
    exact = next((row for row in matches if row["symbol"] == normalized), None)
    if exact is None:
        raise HTTPException(
            status_code=400,
            detail="Please select a valid stock symbol.",
        )
    return normalized


def _validate_price_range(
    *,
    symbol: str,
    trade_date: datetime,
    price: float,
    label: str,
    confirm_out_of_range: bool,
) -> None:
    day_range = get_day_ohlc_range(market_data_service, symbol, _as_date(trade_date))
    if not day_range["available"]:
        return
    low = day_range["low"]
    high = day_range["high"]
    if low is None or high is None:
        return
    if low <= price <= high or confirm_out_of_range:
        return
    raise HTTPException(
        status_code=400,
        detail=(
            f"{label} price ₹{price:.2f} is outside the recorded trading range of "
            f"₹{low:.2f}–₹{high:.2f} for {trade_date.strftime('%d %b %Y')}."
        ),
    )


def _validate_trade_payload(payload: TradeCreate) -> tuple[str, str]:
    symbol = _validate_symbol(payload.symbol)
    has_exit_date = payload.exit_date is not None
    has_exit_price = payload.exit_price is not None

    if has_exit_date != has_exit_price:
        raise HTTPException(
            status_code=400,
            detail="A closed trade requires both Exit Date and Exit Price.",
        )

    if payload.exit_date and _as_date(payload.exit_date) < _as_date(payload.trade_date):
        raise HTTPException(
            status_code=400,
            detail="Exit Date cannot be before Entry Date.",
        )

    status_value = "CLOSED" if has_exit_date and has_exit_price else "OPEN"
    if status_value == "CLOSED" and payload.exit_price is None:
        raise HTTPException(status_code=400, detail="Exit price is required for closed trades.")

    _validate_price_range(
        symbol=symbol,
        trade_date=payload.trade_date,
        price=payload.entry_price,
        label="Entry",
        confirm_out_of_range=payload.confirm_out_of_range,
    )
    if status_value == "CLOSED" and payload.exit_date and payload.exit_price is not None:
        _validate_price_range(
            symbol=symbol,
            trade_date=payload.exit_date,
            price=payload.exit_price,
            label="Exit",
            confirm_out_of_range=payload.confirm_out_of_range,
        )

    return symbol, status_value


def _to_out(trade: Trade) -> TradeOut:
    status_value = trade.status or ("CLOSED" if trade.exit_price is not None else "OPEN")
    side = trade.side or "LONG"
    current_price = None
    unrealized_pnl = None
    holding_period_days = None
    realized_pnl = 0.0
    exit_price = trade.exit_price

    if status_value == "OPEN":
        current_price = _current_price(trade.symbol)
        if current_price is not None:
            unrealized_pnl = _calc_unrealized_pnl(
                side, trade.entry_price, current_price, trade.quantity
            )
    else:
        if exit_price is None:
            exit_price = trade.entry_price
        realized_pnl = _calc_realized_pnl(side, trade.entry_price, exit_price, trade.quantity)
        if trade.exit_date is not None:
            holding_period_days = _holding_period_days(trade.trade_date, trade.exit_date)

    return TradeOut(
        id=trade.id,
        trade_date=trade.trade_date,
        symbol=trade.symbol,
        side=side,  # type: ignore[arg-type]
        entry_price=trade.entry_price,
        exit_price=exit_price if status_value == "CLOSED" else None,
        exit_date=trade.exit_date,
        quantity=trade.quantity,
        notes=trade.notes,
        status=status_value,  # type: ignore[arg-type]
        pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        current_price=current_price,
        holding_period_days=holding_period_days,
    )


@router.get("", response_model=List[TradeOut])
def list_trades(db: Session = Depends(get_db)) -> List[TradeOut]:
    rows = db.scalars(
        select(Trade).order_by(Trade.trade_date.desc(), Trade.id.desc())
    ).all()
    return [_to_out(trade) for trade in rows]


@router.post("", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)) -> TradeOut:
    symbol, status_value = _validate_trade_payload(payload)
    trade = Trade(
        trade_date=payload.trade_date,
        symbol=symbol,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price if status_value == "CLOSED" else None,
        exit_date=payload.exit_date if status_value == "CLOSED" else None,
        quantity=payload.quantity,
        notes=payload.notes or "",
        side=payload.side,
        status=status_value,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return _to_out(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_trade(trade_id: int, db: Session = Depends(get_db)) -> Response:
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    db.delete(trade)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

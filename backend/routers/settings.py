"""Application settings — a single row keyed by id=1."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import Settings
from schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> Settings:
    row = db.scalar(select(Settings).where(Settings.id == 1))
    if row is None:
        row = Settings(id=1, capital=100000.0, risk_per_trade=1.0, preferred_timeframe="1D")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)) -> SettingsOut:
    return SettingsOut.model_validate(_get_or_create(db))


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsOut:
    row = _get_or_create(db)
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return SettingsOut.model_validate(row)

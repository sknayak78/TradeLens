"""Provider-independent market data models used by universe and screening."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Mapping, Sequence

MarketStatusValue = Literal["OPEN", "PRE_OPEN", "CLOSED", "WEEKEND"]
LatencyClass = Literal["instant", "low", "medium", "high"]


@dataclass(frozen=True)
class Instrument:
    """A tradable instrument in the application universe."""

    symbol: str
    name: str
    sector: str = ""
    active: bool = True


@dataclass(frozen=True)
class UniverseConfig:
    """Metadata describing a configured instrument universe."""

    name: str
    active: bool = True
    description: str = ""


@dataclass(frozen=True)
class OpportunityContext:
    """Curated ranking context from the legacy OPPORTUNITIES list."""

    symbol: str
    score: int
    reason: str


@dataclass(frozen=True)
class Quote:
    """Normalized latest quote for one symbol."""

    symbol: str
    price: float
    change_pct: float
    volume: int | None = None
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not math.isfinite(self.price) or self.price <= 0:
            raise ValueError("price must be a positive finite number")
        if not math.isfinite(self.change_pct):
            raise ValueError("change_pct must be finite")


@dataclass(frozen=True)
class OHLCVBar:
    """One completed OHLCV bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{label} must be finite")
        if self.volume is not None and not math.isfinite(self.volume):
            raise ValueError("volume must be finite when provided")


@dataclass(frozen=True)
class MarketStatus:
    """Exchange session state aligned with MarketDataService metadata."""

    status: MarketStatusValue
    as_of: datetime


@dataclass(frozen=True)
class DataFreshness:
    """Provider-side freshness metadata for normalized reads."""

    provider: str
    observed_at: datetime
    latency_class: LatencyClass
    stale: bool = False


@dataclass(frozen=True)
class StockSnapshot:
    """Internal normalized stock row before legacy dict conversion."""

    symbol: str
    name: str
    price: float
    change_pct: float
    rsi: float
    ema20: float
    vwap: float
    volume: int
    trend: str
    day_high: float
    avg_volume: int
    sector: str
    ema50: float | None = None
    ema200: float | None = None
    score: int | None = None
    support: float | None = None
    resistance: float | None = None

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to the legacy provider snapshot consumed by screening and routers."""
        payload: dict[str, Any] = {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "changePct": self.change_pct,
            "rsi": self.rsi,
            "ema20": self.ema20,
            "vwap": self.vwap,
            "volume": self.volume,
            "trend": self.trend,
            "day_high": self.day_high,
            "avg_volume": self.avg_volume,
            "sector": self.sector,
        }
        if self.ema50 is not None:
            payload["ema50"] = self.ema50
        if self.ema200 is not None:
            payload["ema200"] = self.ema200
        if self.score is not None:
            payload["score"] = self.score
        if self.support is not None:
            payload["support"] = self.support
        if self.resistance is not None:
            payload["resistance"] = self.resistance
        return payload


@dataclass(frozen=True)
class StockInsight:
    """Internal normalized chart/support payload before legacy dict conversion."""

    symbol: str
    support: float
    resistance: float
    ai_insight: str
    series: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to the legacy insight dict consumed by stock detail and decide()."""
        return {
            "support": self.support,
            "resistance": self.resistance,
            "aiInsight": self.ai_insight,
            "series": [dict(point) for point in self.series],
        }


def quote_from_snapshot(snapshot: StockSnapshot, *, observed_at: datetime | None = None) -> Quote:
    """Derive a normalized quote from a stock snapshot."""
    return Quote(
        symbol=snapshot.symbol,
        price=snapshot.price,
        change_pct=snapshot.change_pct,
        volume=snapshot.volume,
        observed_at=observed_at,
    )


def ohlcv_bars_from_insight_series(
    symbol: str,
    series: Sequence[Mapping[str, Any]],
    *,
    base_date: datetime | None = None,
) -> tuple[OHLCVBar, ...]:
    """Build synthetic daily bars from legacy chart series points for tests."""
    when = base_date or datetime(2026, 1, 15)
    bars: list[OHLCVBar] = []
    for index, point in enumerate(series):
        close = float(point["v"])
        bars.append(
            OHLCVBar(
                timestamp=when.replace(hour=9, minute=15 + index),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1.0,
            )
        )
    return tuple(bars)

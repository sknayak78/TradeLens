"""Chart timeframe configuration for market-data series requests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChartTimeframe = Literal["1D", "1W", "1M", "3M", "1Y"]

SUPPORTED_TIMEFRAMES: tuple[ChartTimeframe, ...] = ("1D", "1W", "1M", "3M", "1Y")
DEFAULT_TIMEFRAME: ChartTimeframe = "1W"


@dataclass(frozen=True)
class TimeframeConfig:
    period: str
    interval: str
    max_points: int
    label: str
    intraday: bool = False


TIMEFRAME_CONFIG: dict[str, TimeframeConfig] = {
    "1D": TimeframeConfig(
        period="1d",
        interval="5m",
        max_points=78,
        label="Intraday",
        intraday=True,
    ),
    "1W": TimeframeConfig(
        period="5d",
        interval="30m",
        max_points=65,
        label="1 Week",
        intraday=True,
    ),
    "1M": TimeframeConfig(
        period="1mo",
        interval="1d",
        max_points=22,
        label="1 Month",
    ),
    "3M": TimeframeConfig(
        period="3mo",
        interval="1d",
        max_points=66,
        label="3 Months",
    ),
    "1Y": TimeframeConfig(
        period="1y",
        interval="1d",
        max_points=252,
        label="1 Year",
    ),
}

# Daily fallback when intraday data is unavailable from the provider.
INTRADAY_FALLBACK: dict[str, TimeframeConfig] = {
    "1D": TimeframeConfig(period="5d", interval="1d", max_points=5, label="Recent Sessions"),
    "1W": TimeframeConfig(period="1mo", interval="1d", max_points=22, label="1 Month (daily)"),
}


def normalize_timeframe(value: str | None) -> ChartTimeframe:
    candidate = (value or DEFAULT_TIMEFRAME).strip().upper()
    if candidate in TIMEFRAME_CONFIG:
        return candidate  # type: ignore[return-value]
    return DEFAULT_TIMEFRAME


def get_timeframe_config(timeframe: str) -> TimeframeConfig:
    return TIMEFRAME_CONFIG[normalize_timeframe(timeframe)]

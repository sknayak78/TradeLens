"""Market universe, screening, and normalized market-data abstractions."""

from services.market_data.indicators import (
    calculate_ema,
    calculate_latest_ema,
    calculate_latest_rsi,
    calculate_rsi,
    calculate_rolling_vwap,
    typical_prices,
)
from services.market_data.legacy_adapter import LegacyCatalogueSupport, LegacyProviderAdapter
from services.market_data.models import (
    DataFreshness,
    Instrument,
    LatencyClass,
    MarketStatus,
    MarketStatusValue,
    OHLCVBar,
    OpportunityContext,
    Quote,
    StockInsight,
    StockSnapshot,
    UniverseConfig,
    ohlcv_bars_from_insight_series,
    quote_from_snapshot,
)
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.snapshot_builder import (
    SCREENING_REQUIRED_FIELDS,
    assert_legacy_stock_fields,
    build_legacy_insight_dict,
    build_legacy_opportunity_rows,
    build_legacy_stock_dict,
    build_legacy_stock_from_quote,
)
from services.market_data.universe import InstrumentUniverse, default_universe

__all__ = [
    "DataFreshness",
    "Instrument",
    "InstrumentUniverse",
    "LatencyClass",
    "LegacyCatalogueSupport",
    "LegacyProviderAdapter",
    "MarketStatus",
    "MarketStatusValue",
    "NormalizedMarketDataProvider",
    "OHLCVBar",
    "OpportunityContext",
    "Quote",
    "SCREENING_REQUIRED_FIELDS",
    "StockInsight",
    "StockSnapshot",
    "UniverseConfig",
    "assert_legacy_stock_fields",
    "build_legacy_insight_dict",
    "build_legacy_opportunity_rows",
    "build_legacy_stock_dict",
    "build_legacy_stock_from_quote",
    "calculate_ema",
    "calculate_latest_ema",
    "calculate_latest_rsi",
    "calculate_rsi",
    "calculate_rolling_vwap",
    "default_universe",
    "ohlcv_bars_from_insight_series",
    "quote_from_snapshot",
    "typical_prices",
]

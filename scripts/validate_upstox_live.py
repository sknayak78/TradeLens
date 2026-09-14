#!/usr/bin/env python3
"""Operator probe for a live Upstox data path (NOT part of the test suite).

Run only with a real ``UPSTOX_ACCESS_TOKEN`` (or ``--token``).  It wires the
Upstox provider with the instrument master and reports historical candles,
snapshot/insight provenance, LTP, and chart provenance for a symbol. Useful to
sanity-check a freshly generated instrument master + token before enabling
Upstox in production.

Usage:
    scripts/validate_upstox_live.py [--symbol RELIANCE] [--token TOKEN]
                                    [--master PATH] [--interval 1d]

Exit code is zero only when candles, snapshot, insight, and chart data all
resolve from Upstox.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger("tradelens.tools.validate_upstox_live")
_TOKEN_ENV = "UPSTOX_ACCESS_TOKEN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--token", default=os.environ.get(_TOKEN_ENV, ""))
    parser.add_argument("--master", type=Path, default=None)
    parser.add_argument("--interval", default="1d")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not args.token:
        logger.error("UPSTOX_ACCESS_TOKEN is not set; refusing a live probe")
        return 2

    sys.path.insert(0, str(ROOT_DIR / "backend"))
    os.chdir(ROOT_DIR / "backend")

    from services.providers.seed_provider import SeedProvider
    from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
    from services.providers.upstox_instrument_source import (
        UpstoxInstrumentMasterError,
        load_instrument_master,
    )
    from services.providers.upstox_provider import UpstoxMarketDataProvider
    from services.chart_series import build_chart_series
    from services.market_data_service import MarketDataService

    master_path = args.master
    try:
        if master_path is not None:
            master_mapping = load_instrument_master(master_path)
        else:
            master_mapping = load_instrument_master()
    except UpstoxInstrumentMasterError as exc:
        logger.error("instrument master invalid: %s", exc)
        return 1

    mapper = UpstoxInstrumentMapper(master_mapping=master_mapping)
    provider = UpstoxMarketDataProvider(
        access_token=args.token,
        instrument_mapper=mapper,
        seed_provider=SeedProvider(),
    )
    service = MarketDataService(provider, SeedProvider(), chain=[provider])

    symbol = args.symbol.strip().upper()
    try:
        bars_result = service.get_historical_ohlcv(
            symbol, period="1mo", interval=args.interval
        )
        stock_result = service.get_stock(symbol)
        insight_result = service.get_stock_insight(symbol)
        series, _, timeframe_fallback, _ = build_chart_series(service, symbol, "1M")
    except Exception as exc:
        logger.error("live Upstox read failed for %s: %s", symbol, exc)
        return 1

    if not bars_result.data or stock_result.data is None or not insight_result.data or not series:
        logger.error("live Upstox read returned empty results for %s", symbol)
        return 1

    print(f"symbol={symbol} candles={len(bars_result.data)} interval={args.interval}")
    print(
        f"historicalProvider={bars_result.metadata.provider} "
        f"snapshotProvider={stock_result.metadata.provider} "
        f"insightProvider={insight_result.metadata.provider}"
    )
    print(
        f"price={stock_result.data['price']} "
        f"priceSource={stock_result.data.get('priceSource')} "
        f"changePct={stock_result.data['changePct']}"
    )
    chart_provider = service.provider_status()["activeProvider"]
    print(
        f"chartProvider={service.provider_status()['activeProvider']} "
        f"chartPoints={len(series)} timeframeFallback={timeframe_fallback}"
    )
    return 0 if all(
        metadata.provider == "upstox"
        for metadata in (
            bars_result.metadata,
            stock_result.metadata,
            insight_result.metadata,
        )
    ) and chart_provider == "upstox" and stock_result.data.get("priceSource") == "ltp" and not timeframe_fallback else 1


if __name__ == "__main__":
    sys.exit(main())

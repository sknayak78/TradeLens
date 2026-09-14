"""Deterministic MD-04 broad-universe scanner tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataMetadata, MarketDataResult, MarketDataService
from services.market_scanner import MarketScanner, ScannerConfig
from services.providers.seed_provider import SeedProvider
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
from services.providers.upstox_instrument_source import build_master_payload, load_instrument_master
from services.providers.upstox_provider import UpstoxMarketDataProvider


def _bars(count: int = 80, *, volume: float = 250_000.0) -> list[OHLCVBar]:
    bars: list[OHLCVBar] = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        close = 100.0 + index * 0.8 - (2.0 if index % 3 == 0 else 0.0)
        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(days=index),
                open=close - 0.2,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=volume,
            )
        )
    return bars


class _Service:
    def __init__(self, rows: dict[str, list[OHLCVBar] | Exception]):
        self.rows = rows
        self.calls: list[str] = []

    def get_historical_ohlcv(self, symbol: str, *, period: str, interval: str):
        self.calls.append(symbol)
        value = self.rows[symbol]
        if isinstance(value, Exception):
            raise value
        return MarketDataResult(
            value,
            MarketDataMetadata("upstox", False, datetime.now(timezone.utc), "CLOSED"),
        )


def test_scanner_uses_broad_injected_universe_not_curated_catalogue() -> None:
    service = _Service({"VOLTAS": _bars(), "PIDILITIND": _bars()})
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            "VOLTAS": "NSE_EQ|INE226A01021",
            "PIDILITIND": "NSE_EQ|INE318A01026",
        },
    )

    result = scanner.scan()

    assert scanner.universe_symbols == ("PIDILITIND", "VOLTAS")
    assert result.metrics.universe_count == 2
    assert (
        result.metrics.data_available_count
        >= result.metrics.liquidity_pass_count
        >= result.metrics.trend_pass_count
        >= result.metrics.momentum_pass_count
        >= result.metrics.technical_pass_count
        >= result.metrics.final_candidate_count
    )
    assert set(service.calls) == {"VOLTAS", "PIDILITIND"}
    assert {candidate.symbol for candidate in result.candidates} == {
        "VOLTAS", "PIDILITIND"
    }
    assert all(candidate.instrument_key.startswith("NSE_EQ|") for candidate in result.candidates)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"LOWVOL": _bars(volume=10_000.0)}, "failed_liquidity"),
        ({"BADTREND": list(reversed(_bars()))}, "failed_trend"),
    ],
)
def test_screening_rejection_reasons_are_transparent(overrides, reason: str) -> None:
    service = _Service(overrides)
    result = MarketScanner(service, instrument_mapping={next(iter(overrides)): "NSE_EQ|KEY"}).scan()

    assert result.metrics.final_candidate_count == 0
    assert reason in result.results[0].rejection_reasons


def test_momentum_and_technical_filters_can_reject_independently() -> None:
    momentum_result = MarketScanner(
        _Service({"MOMENTUM": _bars()}),
        instrument_mapping={"MOMENTUM": "NSE_EQ|MOMENTUM"},
        config=ScannerConfig(maximum_momentum_rsi=70.0),
    ).scan()
    technical_result = MarketScanner(
        _Service({"TECHNICAL": _bars()}),
        instrument_mapping={"TECHNICAL": "NSE_EQ|TECHNICAL"},
        config=ScannerConfig(maximum_daily_move_pct=0.1),
    ).scan()

    assert "failed_momentum" in momentum_result.results[0].rejection_reasons
    assert "failed_technical" in technical_result.results[0].rejection_reasons


def test_missing_data_does_not_abort_scan_and_funnel_counts_are_consistent() -> None:
    service = _Service({"GOOD": _bars(), "MISSING": RuntimeError("provider down")})
    result = MarketScanner(
        service,
        instrument_mapping={"GOOD": "NSE_EQ|GOOD", "MISSING": "NSE_EQ|MISSING"},
    ).scan()

    assert result.metrics.universe_count == 2
    assert result.metrics.data_available_count == 1
    assert result.metrics.final_candidate_count == 1
    missing = next(row for row in result.results if row.symbol == "MISSING")
    assert missing.error == "provider down"
    assert missing.rejection_reasons == ("data_unavailable",)


def test_scanner_does_not_call_snapshot_or_deep_analysis() -> None:
    service = _Service({f"STOCK{i:03d}": _bars() for i in range(120)})
    result = MarketScanner(
        service,
        instrument_mapping={f"STOCK{i:03d}": f"NSE_EQ|{i:09d}" for i in range(120)},
    ).scan()

    assert result.metrics.universe_count == 120
    assert len(service.calls) == 120
    assert result.metrics.final_candidate_count <= result.metrics.universe_count


def test_scanner_depends_only_on_market_data_service_boundary() -> None:
    source = (Path(__file__).parents[1] / "services" / "market_scanner.py").read_text()

    for private_or_provider_name in (
        "YahooFinanceProvider",
        "UpstoxMarketDataProvider",
        "SeedProvider",
        "._history",
        "._quote",
        "._primary",
    ):
        assert private_or_provider_name not in source


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload


def test_instrument_master_mapper_service_scanner_broad_integration(tmp_path) -> None:
    records = [
        {
            "symbol": f"STOCK{i:04d}",
            "name": f"Stock {i}",
            "instrument_key": f"NSE_EQ|INE{i:09d}",
        }
        for i in range(1500)
    ]
    records.extend([
        {"symbol": "VOLTAS", "name": "Voltas", "instrument_key": "NSE_EQ|INE226A01021"},
        {"symbol": "PIDILITIND", "name": "Pidilite", "instrument_key": "NSE_EQ|INE318A01026"},
    ])
    path = tmp_path / "master.json"
    path.write_text(json.dumps(build_master_payload(records, version="md04-test")))
    mapping = load_instrument_master(path)
    bars = _bars()
    candles = [
        [bar.timestamp.isoformat(), bar.open, bar.high, bar.low, bar.close, bar.volume]
        for bar in bars
    ]
    fetcher_calls: list[str] = []

    def fetcher(url: str, headers: dict[str, str], timeout: float):
        fetcher_calls.append(url)
        return _FakeResponse({"status": "success", "data": {"candles": candles}})

    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=UpstoxInstrumentMapper(master_mapping=mapping),
        fetcher=fetcher,
    )
    service = MarketDataService(provider, SeedProvider(), chain=[provider])
    result = MarketScanner(service, instrument_mapping=mapping).scan()

    assert result.metrics.universe_count == 1502
    assert {"VOLTAS", "PIDILITIND"}.issubset(set(service_provider_symbols(fetcher_calls)))
    assert all(row.provider == "upstox" for row in result.results if row.error is None)


def service_provider_symbols(urls: list[str]) -> set[str]:
    """The scanner requests instrument keys; recover broad symbols from known keys."""
    return {
        "VOLTAS" if "INE226A01021" in url else "PIDILITIND"
        for url in urls
        if "INE226A01021" in url or "INE318A01026" in url
    }

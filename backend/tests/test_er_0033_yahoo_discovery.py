"""Unit tests for ER-0033: Yahoo Finance instrument discovery and NSE equity support."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock
import pandas as pd

from services.market_data.models import StockSnapshot
from services.providers.seed_provider import SeedMarketDataProvider, SeedProvider
from services.providers.yahoo_discovery import (
    DiscoveredInstrument,
    _is_valid_nse_equity,
    discover_nse_equities,
)
from services.providers.yahoo_finance_provider import (
    YahooFinanceProvider,
    YahooMarketDataProvider,
)
from services.symbol_mapper import SymbolMapper


def _mock_ohlcv_dataframe() -> pd.DataFrame:
    """Generate 30 synthetic daily OHLCV bars for mocking Yahoo history."""
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    data = {
        "Open": [100.0 + i for i in range(30)],
        "High": [105.0 + i for i in range(30)],
        "Low": [95.0 + i for i in range(30)],
        "Close": [102.0 + i for i in range(30)],
        "Volume": [10000 + i * 100 for i in range(30)],
    }
    return pd.DataFrame(data, index=dates)


class TestYahooDiscovery(unittest.TestCase):
    """Test strict filtering, ranking, and alias behavior in Yahoo discovery."""

    def setUp(self) -> None:
        self.mapper = SymbolMapper()

    def test_nse_equity_filtering_accepts_valid_nse_equities(self) -> None:
        valid_quotes = [
            {"symbol": "RELIANCE.NS", "exchange": "NSI", "quoteType": "EQUITY"},
            {"symbol": "TCS.NS", "exchange": "NSE", "quoteType": "EQUITY"},
            {"symbol": "ETERNAL.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Eternal Limited"},
        ]
        for quote in valid_quotes:
            self.assertTrue(_is_valid_nse_equity(quote), f"Failed to accept valid quote: {quote}")

    def test_nse_equity_filtering_rejects_adrs_and_foreign_listings(self) -> None:
        foreign_quotes = [
            {"symbol": "INFY", "exchange": "NYQ", "quoteType": "EQUITY"},  # NYSE ADR
            {"symbol": "RS", "exchange": "NYQ", "quoteType": "EQUITY"},  # Reliance US
            {"symbol": "TCS.DE", "exchange": "GER", "quoteType": "EQUITY"},  # German listing
            {"symbol": "TCS.TO", "exchange": "TOR", "quoteType": "EQUITY"},  # Toronto listing
            {"symbol": "0221.KL", "exchange": "KLS", "quoteType": "EQUITY"},  # Malaysia listing
        ]
        for quote in foreign_quotes:
            self.assertFalse(_is_valid_nse_equity(quote), f"Failed to reject foreign quote: {quote}")

    def test_nse_equity_filtering_rejects_bse_listings(self) -> None:
        bse_quotes = [
            {"symbol": "RELINFRA.BO", "exchange": "BSE", "quoteType": "EQUITY"},
            {"symbol": "INFY.BO", "exchange": "BSE", "quoteType": "EQUITY"},
        ]
        for quote in bse_quotes:
            self.assertFalse(_is_valid_nse_equity(quote), f"Failed to reject BSE quote: {quote}")

    def test_nse_equity_filtering_rejects_etfs_and_mutual_funds(self) -> None:
        non_equities = [
            {"symbol": "NIFTYBEES.NS", "exchange": "NSI", "quoteType": "ETF"},
            {"symbol": "TCSH.TO", "exchange": "TOR", "quoteType": "ETF"},
            {"symbol": "0P0000XW01.BO", "exchange": "BSE", "quoteType": "MUTUALFUND"},
        ]
        for quote in non_equities:
            self.assertFalse(_is_valid_nse_equity(quote), f"Failed to reject non-equity: {quote}")

    def test_nse_equity_filtering_rejects_indices_and_derivatives(self) -> None:
        derivatives_and_indices = [
            {"symbol": "^NSEI", "exchange": "NSI", "quoteType": "INDEX"},
            {"symbol": "NIFTY26AUG24500CE.NS", "exchange": "NSI", "quoteType": "OPTION"},
        ]
        for quote in derivatives_and_indices:
            self.assertFalse(_is_valid_nse_equity(quote), f"Failed to reject index/derivative: {quote}")

    def test_exact_ticker_ranking_ranks_exact_symbol_first(self) -> None:
        mock_quotes = [
            {"symbol": "RS", "exchange": "NYQ", "quoteType": "EQUITY", "score": 20015.0},
            {"symbol": "RELINFRA.BO", "exchange": "BSE", "quoteType": "EQUITY", "score": 20011.0},
            {"symbol": "RELCHEMQ.NS", "exchange": "NSI", "quoteType": "EQUITY", "score": 20003.0, "shortname": "RELIANCE CHEMOTEX"},
            {"symbol": "RELIANCE.NS", "exchange": "NSI", "quoteType": "EQUITY", "score": 20007.0, "shortname": "RELIANCE INDUSTRIES LTD"},
        ]

        def mock_fetcher(query: str, max_results: int) -> list[dict]:
            return mock_quotes

        results = discover_nse_equities("RELIANCE", search_fetcher=mock_fetcher)
        self.assertGreaterEqual(len(results), 2)
        # RELIANCE should be #1 despite raw Yahoo score/ordering
        self.assertEqual(results[0].symbol, "RELIANCE")
        self.assertEqual(results[0].yahoo_symbol, "RELIANCE.NS")
        self.assertEqual(results[1].symbol, "RELCHEMQ")

    def test_company_name_search_ranks_relevant_nse_equities(self) -> None:
        mock_quotes = [
            {"symbol": "TCS.DE", "exchange": "GER", "quoteType": "EQUITY"},
            {"symbol": "TCS.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Tata Consultancy Services Limited", "shortname": "TATA CONSULTANCY SERV LT"},
            {"symbol": "TATAMOTORS.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Tata Motors Limited", "shortname": "TATA MOTORS LTD"},
        ]

        def mock_fetcher(query: str, max_results: int) -> list[dict]:
            return mock_quotes

        results = discover_nse_equities("Tata Consultancy Services", search_fetcher=mock_fetcher)
        self.assertEqual(results[0].symbol, "TCS")
        self.assertEqual(results[0].name, "Tata Consultancy Services Limited")

    def test_corporate_alias_zomato_to_eternal(self) -> None:
        self.assertEqual(self.mapper.resolve_alias("ZOMATO"), "ETERNAL")
        self.assertEqual(self.mapper.resolve_alias("zomato"), "ETERNAL")
        self.assertEqual(self.mapper.to_yahoo("ZOMATO"), "ETERNAL.NS")
        self.assertEqual(self.mapper.to_canonical("ETERNAL.NS"), "ETERNAL")

        mock_quotes = [
            {"symbol": "ETERNAL.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Eternal Limited", "shortname": "ETERNAL LIMITED", "score": 20000.0},
        ]

        def mock_fetcher(query: str, max_results: int) -> list[dict]:
            if "ETERNAL" in query.upper() or "ZOMATO" in query.upper():
                return mock_quotes
            return []

        results = discover_nse_equities("Zomato", search_fetcher=mock_fetcher, symbol_mapper=self.mapper)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].symbol, "ETERNAL")
        self.assertEqual(results[0].name, "Eternal Limited")


class TestDynamicHydration(unittest.TestCase):
    """Test dynamic hydration of non-seed NSE equities and preservation of seed fallback."""

    def setUp(self) -> None:
        self.seed_provider = SeedMarketDataProvider()
        self.history_df = _mock_ohlcv_dataframe()
        self.mock_history_fetcher = MagicMock(return_value=self.history_df)
        self.mock_quote_fetcher = MagicMock(return_value=(325.50, 1.75, 500000))

        self.provider = YahooMarketDataProvider(
            self.seed_provider,
            history_fetcher=self.mock_history_fetcher,
            quote_fetcher=self.mock_quote_fetcher,
        )

    def test_dynamic_hydration_of_non_seed_nse_symbol(self) -> None:
        # 'ETERNAL' is not in the seed catalogue
        self.assertIsNone(self.seed_provider.stock_snapshot("ETERNAL"))

        self.provider.register_discovered_instrument("ETERNAL", "Eternal Limited", "Consumer Cyclical")
        snapshot = self.provider.stock_snapshot("ETERNAL")

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.symbol, "ETERNAL")
        self.assertEqual(snapshot.name, "Eternal Limited")
        self.assertEqual(snapshot.sector, "Consumer Cyclical")
        self.assertEqual(snapshot.price, 325.50)
        self.assertEqual(snapshot.change_pct, 1.75)
        self.assertGreater(snapshot.rsi, 0)
        self.assertGreater(snapshot.ema20, 0)
        self.assertGreater(snapshot.vwap, 0)

        insight = self.provider.stock_insight("ETERNAL")
        self.assertIsNotNone(insight)
        assert insight is not None
        self.assertEqual(insight.symbol, "ETERNAL")
        self.assertGreater(len(insight.series), 0)

    def test_seed_stock_preserves_seed_metadata_and_fallback(self) -> None:
        # Seed stock RELIANCE
        seed_snap = self.seed_provider.stock_snapshot("RELIANCE")
        self.assertIsNotNone(seed_snap)

        snapshot = self.provider.stock_snapshot("RELIANCE")
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.symbol, "RELIANCE")
        self.assertEqual(snapshot.name, seed_snap.name)  # Preserves official seed name

        # If Yahoo fails for seed stock, it falls back to seed snapshot
        failing_provider = YahooMarketDataProvider(
            self.seed_provider,
            history_fetcher=MagicMock(side_effect=RuntimeError("Yahoo offline")),
            quote_fetcher=MagicMock(side_effect=RuntimeError("Yahoo offline")),
        )
        fallback_snapshot = failing_provider.stock_snapshot("RELIANCE")
        self.assertIsNotNone(fallback_snapshot)
        assert fallback_snapshot is not None
        self.assertEqual(fallback_snapshot.symbol, "RELIANCE")
        self.assertEqual(fallback_snapshot.price, seed_snap.price)

    def test_search_stock_snapshots_merges_discovered_and_seed_matches(self) -> None:
        mock_discovered = [
            {"symbol": "ETERNAL.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Eternal Limited", "score": 20000.0},
        ]
        self.provider.bind_search_fetcher(lambda q, limit: mock_discovered if "ETERNAL" in q.upper() or "ZOMATO" in q.upper() else [])

        results = self.provider.search_stock_snapshots("Eternal", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].symbol, "ETERNAL")

    def test_search_stock_snapshots_omits_unhydrated_discovered_instruments(self) -> None:
        # Discovered 2 non-seed instruments: one hydrates, one fails
        mock_discovered = [
            {"symbol": "HYDRATED.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Hydrated Ltd", "score": 20000.0},
            {"symbol": "UNHYDRATED.NS", "exchange": "NSI", "quoteType": "EQUITY", "longname": "Unhydrated Ltd", "score": 19000.0},
        ]
        self.provider.bind_search_fetcher(lambda q, limit: mock_discovered)

        def selective_history_fetcher(ticker: str, period: str = "2y", interval: str = "1d"):
            if ticker.startswith("HYDRATED"):
                return self.history_df
            raise RuntimeError(f"Yahoo history unavailable for {ticker}")

        self.provider.bind_history_fetcher(selective_history_fetcher)

        results = self.provider.search_stock_snapshots("test", limit=5)
        returned_symbols = [snap.symbol for snap in results]

        # HYDRATED should be present with valid price
        self.assertIn("HYDRATED", returned_symbols)
        # UNHYDRATED should be omitted completely, not returned with price=0.0
        self.assertNotIn("UNHYDRATED", returned_symbols)
        for snap in results:
            self.assertNotEqual(snap.price, 0.0, f"Found snapshot with 0.0 price: {snap.symbol}")



class TestLegacyFaçadeAndTradeValidation(unittest.TestCase):
    """Test that LegacyProviderAdapter and trade validation flow work with discovered symbols."""

    def test_adapter_hydrates_non_seed_stock_into_legacy_dict(self) -> None:
        seed_provider = SeedProvider()
        history_df = _mock_ohlcv_dataframe()
        mock_history = MagicMock(return_value=history_df)
        mock_quote = MagicMock(return_value=(2500.0, 0.8, 120000))

        yahoo_provider = YahooFinanceProvider(
            seed_provider=seed_provider,
        )
        yahoo_provider._normalized.bind_history_fetcher(mock_history)
        yahoo_provider._normalized.bind_quote_fetcher(mock_quote)
        yahoo_provider._normalized.register_discovered_instrument("PIDILITIND", "Pidilite Industries", "Basic Materials")

        stock = yahoo_provider.get_stock("PIDILITIND")
        self.assertIsNotNone(stock)
        assert stock is not None
        self.assertEqual(stock["symbol"], "PIDILITIND")
        self.assertEqual(stock["name"], "Pidilite Industries")
        self.assertEqual(stock["price"], 2500.0)
        self.assertIn("rsi", stock)
        self.assertIn("ema20", stock)
        self.assertIn("vwap", stock)

        insight = yahoo_provider.get_stock_insight("PIDILITIND")
        self.assertIsNotNone(insight)
        self.assertIn("support", insight)
        self.assertIn("resistance", insight)
        self.assertIn("series", insight)


if __name__ == "__main__":
    unittest.main()

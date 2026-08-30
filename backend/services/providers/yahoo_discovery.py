"""Yahoo Finance instrument discovery for NSE equities.

Strictly filters and ranks search results to return canonical NSE equities,
filtering out ADRs, foreign listings, BSE listings, ETFs, mutual funds,
and derivatives.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable, Sequence

from services.symbol_mapper import SymbolMapper

logger = logging.getLogger("tradelens.market_data.yahoo_discovery")

SearchFetcher = Callable[[str, int], Any]


@dataclass(frozen=True)
class DiscoveredInstrument:
    """Canonical NSE equity discovered via Yahoo search."""

    symbol: str  # Canonical TradeLens symbol (e.g., 'RELIANCE', 'ETERNAL')
    yahoo_symbol: str  # Provider ticker (e.g., 'RELIANCE.NS')
    name: str
    sector: str
    exchange: str
    quote_type: str
    score: float


def _default_search_fetcher(query: str, max_results: int) -> list[dict[str, Any]]:
    """Execute yf.Search with the given query and max results."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed") from exc

    search = yf.Search(query, max_results=max_results)
    return getattr(search, "quotes", []) or []


def _is_valid_nse_equity(quote: dict[str, Any]) -> bool:
    """Verify if a Yahoo search quote is a valid NSE equity."""
    quote_type = (quote.get("quoteType") or quote.get("typeDisp") or "").strip().upper()
    if quote_type != "EQUITY":
        return False

    exchange = (quote.get("exchange") or quote.get("exchDisp") or "").strip().upper()
    raw_symbol = (quote.get("symbol") or "").strip().upper()

    # Reject non-NSE exchanges explicitly (NYQ, NMS, BSE, GER, etc.)
    if exchange in {"BSE", "NYQ", "NMS", "GER", "TOR", "BUE", "MEX", "LSE", "JPX", "SHZ", "TAI", "PNK", "KLS"}:
        return False

    # Check if exchange is NSI/NSE or symbol ends with .NS
    is_nse_exchange = exchange in {"NSI", "NSE"}
    is_nse_symbol = raw_symbol.endswith(".NS")

    if not (is_nse_exchange or is_nse_symbol):
        return False

    # Reject futures, options, derivatives, or index symbols (e.g., ^NSEI, spaces, special chars)
    if raw_symbol.startswith("^") or "=" in raw_symbol or " " in raw_symbol:
        return False

    return True


def _ranking_key(
    instrument: DiscoveredInstrument,
    query: str,
) -> tuple[int, int, int, float, str]:
    """Calculate ranking priority for a discovered instrument.

    Lower tuple values indicate higher rank.
    """
    clean_query = query.strip().upper()
    sym = instrument.symbol.upper()
    name = instrument.name.upper()

    # 1. Symbol match priority: exact (0), starts-with (1), contains (2), none (3)
    if sym == clean_query:
        sym_match = 0
    elif sym.startswith(clean_query):
        sym_match = 1
    elif clean_query in sym:
        sym_match = 2
    else:
        sym_match = 3

    # 2. Name match priority: exact (0), starts-with (1), contains (2), none (3)
    if name == clean_query:
        name_match = 0
    elif name.startswith(clean_query):
        name_match = 1
    elif clean_query in name:
        name_match = 2
    else:
        name_match = 3

    # 3. Combined text length penalty (prefer more concise, direct matches)
    length_penalty = len(sym) + len(name)

    # 4. Inverted Yahoo score (higher Yahoo score -> lower rank tuple value)
    score_penalty = -instrument.score

    return (sym_match, name_match, length_penalty, score_penalty, sym)


def discover_nse_equities(
    query: str,
    *,
    max_results: int = 20,
    search_fetcher: SearchFetcher | None = None,
    symbol_mapper: SymbolMapper | None = None,
) -> list[DiscoveredInstrument]:
    """Discover and rank NSE equities for a search query."""
    clean_query = query.strip()
    if not clean_query:
        return []

    mapper = symbol_mapper or SymbolMapper()
    resolved_query = mapper.resolve_alias(clean_query)

    fetcher = search_fetcher or _default_search_fetcher

    # Fetch quotes for both resolved query and original query if different
    queries_to_try = [resolved_query]
    if resolved_query.upper() != clean_query.upper():
        queries_to_try.append(clean_query)

    raw_quotes: list[dict[str, Any]] = []
    seen_symbols: set[str] = set()

    for q in queries_to_try:
        try:
            results = fetcher(q, max(max_results * 2, 10))
            for item in results:
                raw_sym = (item.get("symbol") or "").strip().upper()
                if raw_sym and raw_sym not in seen_symbols:
                    seen_symbols.add(raw_sym)
                    raw_quotes.append(item)
        except Exception:
            logger.warning("yahoo_discovery.search_failed query=%s", q, exc_info=True)

    discovered: list[DiscoveredInstrument] = []
    seen_canonicals: set[str] = set()

    for quote in raw_quotes:
        if not _is_valid_nse_equity(quote):
            continue

        raw_sym = quote.get("symbol", "").strip()
        canonical = mapper.to_canonical(raw_sym)
        if canonical in seen_canonicals:
            continue
        seen_canonicals.add(canonical)

        name = (
            quote.get("longname")
            or quote.get("shortname")
            or canonical
        ).strip()
        sector = (
            quote.get("sector")
            or quote.get("sectorDisp")
            or quote.get("industry")
            or "Equities"
        ).strip()
        exchange = (quote.get("exchange") or quote.get("exchDisp") or "NSI").strip()
        quote_type = (quote.get("quoteType") or quote.get("typeDisp") or "EQUITY").strip()
        score = float(quote.get("score") or 0.0)

        discovered.append(
            DiscoveredInstrument(
                symbol=canonical,
                yahoo_symbol=raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS",
                name=name,
                sector=sector,
                exchange=exchange,
                quote_type=quote_type,
                score=score,
            )
        )

    # Sort strictly by relevance to the search query
    discovered.sort(key=lambda item: _ranking_key(item, resolved_query))
    return discovered[:max_results]

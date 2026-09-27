# Provider/Broker Adapter Architecture

> TradeLens is the intelligence layer, not the broker. Provider adapters isolate broker-specific APIs and credentials behind a normalized market-data contract.

---

## Purpose

This document defines the provider/broker adapter architecture for TradeLens. It establishes the boundary between provider-specific implementations and the provider-neutral intelligence engine.

---

## Architecture Boundary

```
┌─────────────────────────────────────────────────────────────────┐
│                     INTELLIGENCE ENGINE                         │
│  (Provider-neutral: Discovery, Ranking, Analysis, Scoring)      │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ Normalized Market Data Contract
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PROVIDER ADAPTER LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Upstox    │  │   Yahoo     │  │    HDFC     │  ...        │
│  │  Adapter    │  │  Adapter    │  │  Adapter    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ Provider-Specific APIs & Auth
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL PROVIDERS                           │
│  Upstox API · Yahoo Finance · HDFC InvestRight · Zerodha Kite  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle:** The intelligence engine knows nothing of specific brokers. It consumes only normalized market data.

---

## Provider Adapter Responsibilities

Each provider adapter implements the following contract:

### 1. Authentication & Session Management
- Handle provider-specific auth (OAuth 2.0, API keys, access tokens)
- Token refresh and session lifecycle
- Credential validation at startup
- Graceful degradation on auth failure

### 2. Historical Daily Bars
- Fetch daily OHLCV for a symbol/date range
- Support incremental fetch (since last stored date)
- Handle adjustments (splits, dividends) per provider convention
- Return normalized `DailyBar` records

### 3. Live Market Snapshot
- Fetch current quote for a symbol or bulk quotes for a universe
- Return normalized `LiveQuote` records
- Support streaming/WebSocket where available (Phase 2+)

### 4. Instrument Master
- Fetch/sync tradeable instrument list
- Map provider symbols to TradeLens normalized symbols
- Provide exchange, segment, lot size, tick size
- Handle symbol changes, de-listings, corporate actions

### 5. Error Handling & Rate Limiting
- Provider-specific error mapping to common error types
- Rate limit adherence with backoff
- Circuit breaker for provider outages
- Structured logging without credentials

---

## Normalized Market Data Contract

All adapters emit these canonical types. The intelligence engine consumes only these.

### DailyBar
```python
@dataclass
class DailyBar:
    symbol: str           # Normalized symbol (e.g., "RELIANCE")
    date: date            # Trading date (UTC date of session)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None
    source: str           # Provider identifier: "upstox", "yahoo", etc.
    fetched_at: datetime  # When this bar was fetched/stored
```

### LiveQuote
```python
@dataclass
class LiveQuote:
    symbol: str
    price: Decimal
    change: Decimal
    change_pct: Decimal
    volume: int
    timestamp: datetime   # Quote timestamp (provider time)
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    oi: Optional[int] = None          # Open interest (F&O)
    source: str
```

### Instrument
```python
@dataclass
class Instrument:
    symbol: str           # Normalized symbol
    name: str
    exchange: str         # "NSE", "BSE"
    segment: str          # "EQ", "FO", "CD"
    isin: Optional[str] = None
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.01")
    provider_symbol: str  # Provider-specific symbol
    provider: str         # "upstox", "yahoo", etc.
    active: bool = True
```

---

## Instrument Master

- Single source of truth for tradeable universe
- Populated by adapter(s) at startup and refreshed periodically
- Normalized symbols are the primary key across providers
- Provider-specific symbols stored as `provider_symbol` for reverse mapping
- Supports multi-provider symbol resolution (same ISIN → same normalized symbol)

---

## Authentication

### Credential Configuration
Credentials are provided **only via environment variables**:

```bash
# Upstox
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_REDIRECT_URI=http://localhost:8001/callback/upstox

# HDFC (when implemented)
HDFC_CLIENT_ID=your_client_id
HDFC_CLIENT_SECRET=your_client_secret

# Zerodha (when implemented)
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
```

### Credential Handling Rules (Non-Negotiable)

| Rule | Enforcement |
|------|-------------|
| Credentials remain on backend/runtime | Never passed to frontend/mobile |
| Never committed to Git | `.env*` in `.gitignore`; pre-commit hooks |
| Never logged | Structured logging filters credential fields |
| Never in diagnostics | Error reports sanitize credential references |
| Never in API responses | Response models exclude credential fields |
| Adapter-isolated | Each adapter manages only its own credentials |

### Auth Flows by Provider

| Provider | Auth Type | Token Lifetime | Refresh |
|----------|-----------|----------------|---------|
| Upstox | OAuth 2.0 (Authorization Code) | 24 hours (access), 30 days (refresh) | Automatic via refresh token |
| Yahoo | None (public API) | N/A | N/A |
| HDFC | OAuth 2.0 / API Key | TBD | TBD |
| Zerodha | OAuth 2.0 (Kite Connect) | Session-based | Manual re-login or token refresh |

---

## Read-Only Scope

**Initial provider integrations are READ-ONLY.**

Adapters expose only:
- Market data (historical bars, live quotes)
- Instrument master
- Market status (open/closed, holidays)

Adapters do NOT expose in initial scope:
- Order placement / modification / cancellation
- Portfolio / positions / holdings
- Funds / margins
- Trade execution reporting

Future trading capability would require a separate `TradingAdapter` extension with explicit user consent and additional security review.

---

## Yahoo Standalone Mode

- **No credentials required** — works out of the box
- Default development provider (`MARKET_DATA_PROVIDER=yahoo`)
- Valid production deployment for users without broker accounts
- Rate limits apply; graceful fallback to cached data
- Serves as reference implementation for adapter contract

---

## Current Implementations

### Upstox Adapter — IMPLEMENTED / VALIDATED
- **Location:** `backend/services/providers/upstox/`
- **Auth:** OAuth 2.0 with automatic token refresh
- **Historical Bars:** `/historical/v2/candles` endpoint
- **Live Quotes:** `/market-quote/quotes` (bulk v3, 500 instruments per request)
- **Instruments:** `/market-quote/instruments` (master download)
- **Rate Limits:** 10 req/sec (auth), 30 req/sec (data)
- **Phase 2 Live Edge:** Bounded concurrency, 429 retry/backoff, missing-instrument tolerance, forming-bar overlay during OPEN market
- **Status:** Read-only market data; production-ready; live validation: 2,655 usable / 1 missing (TAALTECH)

### Yahoo Adapter — IMPLEMENTED
- **Location:** `backend/services/providers/yahoo/`
- **Auth:** None
- **Historical Bars:** `yfinance` library (daily intervals)
- **Live Quotes:** `yfinance` fast_info / quote
- **Instruments:** Curated NSE equity list + search
- **Rate Limits:** Unofficial; implements polite delays
- **Status:** Standalone/fallback; production-ready

---

## Next Integration: HDFC Securities / InvestRight — NEXT / PLANNED

- **Auth:** OAuth 2.0 (InvestRight API)
- **Endpoints:** Historical candles, live quotes, instrument master
- **Challenges:** Session management, rate limits, symbol mapping
- **Priority:** Next after Phase 2 completion

---

## Future Provider Roadmap

| Provider | Auth Style | Notes |
|----------|------------|-------|
| Zerodha / Kite | OAuth 2.0 (Kite Connect) | Mature API, WebSocket support |
| Groww | API Key + Session | Private API; may need reverse engineering |
| Angel One / SmartAPI | OAuth 2.0 | WebSocket for live data |
| ICICI Direct / Breeze | API Key + Session | REST + WebSocket |

---

## How to Add a Provider

1. **Create adapter package**: `backend/services/providers/<provider>/`
2. **Implement interface**: `ProviderAdapter` abstract base class
3. **Define config**: Environment variables for credentials
4. **Implement methods**:
   - `authenticate() -> bool`
   - `fetch_daily_bars(symbol, start, end) -> List[DailyBar]`
   - `fetch_live_quotes(symbols) -> List[LiveQuote]`
   - `sync_instruments() -> List[Instrument]`
5. **Register in factory**: `ProviderAdapterFactory.register("provider", AdapterClass)`
6. **Add tests**: Unit tests with mocked HTTP; integration test with real credentials (manual)
7. **Update docs**: Add provider to this document's status table
8. **Security review**: Credential handling, logging, error paths

---

## Testing Requirements

### Unit Tests (per adapter)
- Authentication flow (success, expiry, refresh, failure)
- Daily bar fetch (single, range, empty, pagination)
- Live quote fetch (single, bulk, missing symbols)
- Instrument sync (full, incremental)
- Error mapping (rate limit, auth failure, network, malformed response)
- Rate limit adherence

### Integration Tests (manual, with real credentials)
- End-to-end historical fetch for 10+ symbols
- Live quote fetch during market hours
- Instrument master sync completeness
- Token refresh across session boundary

### Contract Tests (shared)
- All adapters return valid `DailyBar`, `LiveQuote`, `Instrument`
- Normalized symbol consistency across providers
- Date/time handling (timezone, market holidays)
- Idempotent daily bar writes (upsert)

---

## Security Requirements

1. **Credential Storage**: Environment variables only; no config files, no database
2. **Memory Handling**: Credentials not logged; cleared from memory after auth where possible
3. **Network**: HTTPS only; certificate validation enabled
4. **Audit Trail**: Adapter logs provider calls (endpoint, latency, status) without credentials
5. **Incident Response**: Credential rotation procedure documented per provider
6. **Dependency Review**: Provider SDKs vetted for supply chain security

---

## Configuration

```python
# backend/config/providers.py
PROVIDER_CONFIG = {
    "yahoo": {
        "enabled": True,
        "priority": 1,  # Fallback priority
        "requires_credentials": False,
    },
    "upstox": {
        "enabled": True,
        "priority": 0,  # Primary when configured
        "requires_credentials": True,
        "credentials": ["UPSTOX_API_KEY", "UPSTOX_API_SECRET"],
    },
    "hdfc": {
        "enabled": False,  # Not yet implemented
        "priority": 2,
        "requires_credentials": True,
    },
}
```

Active provider selected by `MARKET_DATA_PROVIDER` env var (default: `yahoo`).

---

## References

- ADR-003: Provider/Broker Adapter Strategy (`docs/05-engineering/ARCHITECTURE_DECISIONS.md`)
- ADR-004: Deterministic Market Intelligence Pipeline
- ADR-006: Market Intelligence Cache and Prepared Data
- `docs/architecture/MARKET_INTELLIGENCE_ARCHITECTURE.md`
- `docs/architecture/TRADELENS_SCORE_INTELLIGENCE_MODEL.md`
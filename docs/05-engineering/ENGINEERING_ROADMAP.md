# TradeLens Engineering Roadmap

> Vision: Build an open-source, self-hosted market-intelligence and investment-research platform for Indian markets.

---

## Product Direction

TradeLens is the **intelligence layer**, not the broker.

Users self-host TradeLens on their own infrastructure and bring their own broker/data-provider entitlements and credentials.

Initial provider integrations are **READ-ONLY** for market research and intelligence.

Order execution is **NOT** part of the initial integration scope.

---

## Documentation Status Legend

| Label | Meaning |
|-------|---------|
| **IMPLEMENTED** | Exists in code and has been validated |
| **ACCEPTED** | Approved architecture/product direction; implementation may be pending or in progress |
| **PLANNED** | Future work not yet implemented |

---

## Phase 1 — IMPLEMENTED

### Core Platform
- Provider/Broker adapter architecture
- Yahoo Finance standalone/fallback mode
- Upstox market-data integration (read-only)
- SQLite persistence with SQLAlchemy
- FastAPI backend, React/TypeScript frontend

### Market Data & Persistence
- Persistent daily-bar storage (OHLCV)
- Restart-safe daily-bar persistence
- Completed daily data reuse outside market hours
- Cache expiry aligned to next NSE pre-open
- Single-flight protection for concurrent `/api/opportunities` computation

### Intelligence & Analytics
- Technical indicators: EMA (20/50/200), RSI, VWAP (rolling 20-session), Support/Resistance
- Recommendation Engine v1.1 (authoritative single source of truth)
- Strategy-driven recommendations (Trend Continuation, Pullback, Breakout, Consolidation, No Entry Yet)
- Deterministic scoring pipeline — no LLM in authoritative path
- AI synthesis/explanation layer (separate from scoring)

### API & Client
- REST APIs for market data, recommendations, watchlist, trade journal, settings
- React web client (Dashboard, Stock Detail, Guided Research, Watchlist, Trade Journal, Settings)
- OpenAPI schema with deprecated legacy fields documented

### Engineering Requests (Completed)
- ER-0004: Live Historical OHLCV Data → **IMPLEMENTED**
- ER-0005: Technical Indicator Engine → **IMPLEMENTED**
- ER-0006: Analysis Engine → **IMPLEMENTED** (as Recommendation Engine v1.1)
- ER-0014: Recommendation Engine v1.1 → **IMPLEMENTED**
- ER-0014A: Recommendation Logic Calibration → **IMPLEMENTED**
- ER-0014B: Establish Recommendation as Single Source of Truth → **IMPLEMENTED**
- ER-0016: Strategy-Driven Recommendation Engine → **IMPLEMENTED**

---

## Phase 2 — IMPLEMENTED / VALIDATED

### Upstox Live Edge
- Provider-neutral live market snapshot abstraction
- Upstox bulk v3 market-quote/quotes integration (500 instruments per request)
- 2,656-instrument universe handled in 6 bulk requests with bounded concurrency
- 429 retry/backoff with missing-instrument tolerance
- Forming-bar overlay during OPEN market session; existing historical bars intact
- Live snapshot caching with single-flight protection
- Yahoo standalone mode remains supported
- 32 deterministic Phase 2 tests
- Live validation: 2,655 usable instruments, 1 known missing/non-traded (TAALTECH)
- Measured live snapshot acquisition ~0.78s (not a guaranteed SLA)

### Scope Boundaries
- Does NOT include incremental historical refresh (PLANNED)
- Does NOT include continuous/background intelligence refresh (PLANNED)
- Does NOT include new provider integrations

---

## Approved Next Phases

### Phase 3 — Incremental Historical Refresh — PLANNED
- Efficient backfill of missing historical daily bars
- Provider-agnostic historical data synchronization
- Gap detection and repair

### Phase 4 — Continuous/Background Market Intelligence — PLANNED
- Background intelligence computation
- Prepared intelligence APIs (avoid full-universe synchronous scans)
- Event-driven refresh triggers

### Phase 5 — HDFC Securities / InvestRight Integration — NEXT / PLANNED
- Read-only market data adapter
- Instrument master alignment
- Authentication flow for HDFC InvestRight

### Phase 6+ — Additional Provider Integrations — PLANNED
| Provider | Status |
|----------|--------|
| Zerodha / Kite | PLANNED |
| Groww | PLANNED |
| Angel One / SmartAPI | PLANNED |
| ICICI Direct / Breeze | PLANNED |

---

## Future Clients — PLANNED

- React Native / Expo mobile application
- Backend APIs remain client-independent

---

## Historical References

The following Engineering Requests and Milestone Documents represent completed work and architectural evolution. They are preserved for context.

### Completed Engineering Requests
- ER-0001 through ER-0003: Initial scaffolding and provider abstraction
- ER-0007: Developer Mode (Backlog)
- ER-0014/14A/14B: Recommendation Engine v1.1 series
- ER-0016: Strategy-Driven Recommendation Engine
- ER-0029: Launch / Education Reliability
- ER-0030: Trade Lifecycle / Mentor Snapshot
- ER-0031: Chart Timeline / X-Axis
- ER-0032: 1Y Chart Correction + CTA Removal
- ER-0036: Persistent Trading Setup & Setup Progress (backend capability)

### Milestone Documents (MD-04 through MD-08)
- MD-04: Market Data Provider Abstraction
- MD-05: Recommendation Engine Architecture
- MD-06: AI Mentor Architecture
- MD-07: Technical Indicator Engine
- MD-08: Chart & Visualization Architecture

These documents capture the as-implemented architecture at their respective milestones and remain valid historical references.

---

## Architecture Decision Records

See `docs/05-engineering/ARCHITECTURE_DECISIONS.md` for:
- ADR-001: Single Source of Truth for Market Data
- ADR-002: Strategy is the Parent Trading Thesis
- ADR-003: Provider/Broker Adapter Strategy (IMPLEMENTED / VALIDATED)
- ADR-004: Deterministic Market Intelligence Pipeline (IMPLEMENTED / VALIDATED)
- ADR-005: AI Synthesis Boundary (IMPLEMENTED / VALIDATED)
- ADR-006: Market Intelligence Cache and Prepared Data (IMPLEMENTED — Phase 1 + Phase 2 live snapshot)

---

## Key Architectural Boundaries (Non-Negotiable)

1. **Credentials never leave backend** — Provider secrets stay on user's runtime
2. **No LLM in scoring path** — TradeLens Score is deterministic
3. **Read-only initial scope** — No order execution in provider adapters
4. **Provider neutrality** — Intelligence engine knows nothing of specific brokers
4. **Self-hosted** — User owns infrastructure and data
5. **Yahoo standalone** — Works without any broker credentials
# TradeLens Architecture Decision Records (ADR)

---

## ADR-001: Single Source of Truth for Market Data

**Status:** Accepted

**Date:** 03-Aug-2026

### Context

The initial implementation overlaid live Yahoo Finance prices onto seeded demo data.

This resulted in inconsistencies such as:

- Live Price from Yahoo Finance
- Seed-generated EMA
- Seed-generated RSI
- Seed-generated VWAP
- Seed-generated chart
- AI insights based on seed indicators

Although useful as a proof of concept, this architecture produced misleading analysis.

### Decision

TradeLens shall use **one and only one source of market data** for each response.

All technical indicators, charts, AI insights and trading recommendations must be derived from the same OHLCV dataset.

### Consequences

Benefits

- Consistent charts
- Consistent indicators
- Trustworthy AI explanations
- Easier testing
- Easy provider replacement (Yahoo, Upstox, HDFC, etc.)

Trade-offs

- Slightly more computation
- Requires historical data retrieval
- Indicator engine must be implemented

---

## ADR-002: Strategy is the Parent Trading Thesis

**Status:** Accepted

**Date:** 07-Aug-2026

**Request:** ER-0016

### Context

The Recommendation Engine scored action, computed a pullback-style entry zone, labelled a strategy afterwards, and built Watch Next from action + limits. That produced contradictory cards — e.g. Strategy = Breakout with Entry Range = buy 3294–3445 **and** Watch Next = wait for a close above 3485.

### Decision

**Strategy is the parent decision.** Pipeline order:

```
score → trend → candidate zone → limits → STRATEGY
                                          ↓
                    action · published levels · narrative · risks
```

- One recommendation = one strategy = one thesis.
- Levels publish only for `Trend Continuation` and `Pullback`.
- `Breakout`, `Consolidation`, and `No Entry Yet` never publish a buy-now entry.
- Narrative receives `strategy` and derives Watch Next / entry condition from it.
- `Fresh Entry` is renamed to `Trend Continuation` (timing is not a strategy).

### Consequences

- Cards cannot invite a buy-now entry while also asking the trader to wait.
- Strategy vocabulary matches the product brief (plus `No Entry Yet` for Avoid).
- Frontend / schema literals updated in the same change; no other API shape moves.

See `docs/05-engineering/ER-0016-STRATEGY-DRIVEN-RECOMMENDATION-ENGINE.md` for before/after examples.

---

## ADR-003: Provider/Broker Adapter Strategy

**Status:** Implemented / Validated

**Date:** 2026

### Context

TradeLens must support multiple market data providers (Upstox, Yahoo, HDFC, Zerodha, Groww, Angel One, ICICI) while keeping the intelligence engine provider-neutral. Credentials are user-owned secrets that must never leave the backend.

### Decision

TradeLens uses a **Provider/Broker Adapter** pattern:

1. **Adapter Interface**: Each provider implements a standard contract for:
   - Authentication (OAuth, API keys, session management)
   - Market data fetch: historical daily bars, live quotes/bulk quotes
   - Instrument master synchronization
   - Error handling and rate limiting

2. **Normalized Market Data**: All adapters emit the same normalized structures:
   - `DailyBar`: date, open, high, low, close, volume, symbol
   - `LiveQuote`: symbol, price, change, volume, timestamp
   - `Instrument`: symbol, name, exchange, segment, lot_size, tick_size

3. **Credential Isolation**:
   - Provider credentials configured via environment variables only
   - Credentials never passed to frontend/mobile clients
   - Credentials never logged, never in API responses, never committed
   - Each adapter manages its own auth lifecycle (token refresh, session)

4. **Read-Only Initial Scope**:
   - Adapters expose only market data endpoints
   - No order placement, portfolio, or trading APIs in initial scope
   - Future trading capability would require separate adapter extension

5. **Yahoo Standalone Mode**:
   - Yahoo Finance adapter requires no credentials
   - Serves as default development and fallback provider
   - Valid production deployment without any broker account

6. **Provider Roadmap**:
    - Upstox: IMPLEMENTED / VALIDATED (read-only market data, live bulk snapshot, forming-bar overlay)
    - Yahoo: IMPLEMENTED (standalone/fallback)
    - HDFC Securities / InvestRight: NEXT (PLANNED)
    - Zerodha / Kite: PLANNED
    - Groww: PLANNED
    - Angel One / SmartAPI: PLANNED
    - ICICI Direct / Breeze: PLANNED

### Consequences

- Intelligence engine depends only on normalized data, never on provider specifics
- New providers added by implementing adapter interface without touching intelligence code
- Credential security enforced by architecture boundary
- Yahoo fallback ensures zero-config development and resilience

---

## ADR-004: Deterministic Market Intelligence Pipeline

**Status:** Implemented / Validated

**Date:** 2026

### Context

Market intelligence must be trustworthy, auditable, and free from non-deterministic influences. The scoring path must not depend on LLM calls, network requests, clock time, or randomness.

### Decision

The market intelligence pipeline follows a strictly deterministic path:

```
Provider/Broker Adapter
        ↓
Normalized Market Data (Daily Bars + Live Snapshot)
        ↓
Market Intelligence
        ├── Discovery (universe filtering, ranking)
        ├── Ranking (relative strength, momentum, structure)
        ├── Deep Analysis (per-symbol technical evidence)
        ↓
Deterministic Analytics
        ├── Technical Indicators (EMA, RSI, VWAP, S/R, ATR)
        ├── Trend Classification
        ├── Support/Resistance Geometry
        ├── Risk/Reward Computation
        ↓
TradeLens Score (deterministic, authoritative)
        ↓
AI Synthesis / Explanation (separate, non-authoritative)
        ↓
Client APIs
```

### Rules

1. **TradeLens Score is deterministic** — identical inputs always produce identical score
2. **No LLM in scoring path** — LLM calls are isolated to the synthesis/explanation layer
3. **No network dependency** in scoring — all data pre-fetched and normalized
4. **No clock/randomness dependency** — pure function of market data
5. **Evidence-first** — every score component traces to observable market evidence
6. **AI explains, never overrides** — synthesis layer receives score + evidence, produces narrative

### Consequences

- Scores are reproducible and backtestable
- AI hallucination cannot affect authoritative recommendation
- Debugging/tracing: every score decision has evidence trail
- Regulatory/audit friendly: deterministic logic, explainable output

---

## ADR-005: AI Synthesis Boundary

**Status:** Implemented / Validated

**Date:** 2026

### Context

AI/LLM capabilities are valuable for explanation, education, and synthesis. They must not compromise the deterministic, authoritative nature of the TradeLens Score.

### Decision

The AI/LLM layer is strictly bounded:

**AI MAY:**
- Synthesize natural-language explanation of deterministic evidence
- Translate technical evidence into beginner-friendly narrative
- Answer user questions about market concepts (educational)
- Generate "why this score" summaries from provided evidence
- Suggest "what to watch next" based on deterministic triggers

**AI MUST NOT:**
- Calculate or influence the TradeLens Score
- Override or adjust any deterministic analytics output
- Introduce new evidence not present in the normalized market data
- Make predictions presented as authoritative
- Be in the critical path for recommendation API responses

**Architectural Enforcement:**
- Scoring service has zero LLM dependencies
- Synthesis service receives (score, evidence, strategy, levels) as input
- Synthesis is async/non-blocking; recommendation API returns without it
- Frontend renders authoritative recommendation first; AI explanation loads separately

### Consequences

- Authoritative recommendation remains fast and deterministic
- AI failure/degradation does not break core product
- Clear separation enables independent evolution of both layers
- User trust: "TradeLens Score" vs "AI Explanation" are visually distinct

---

## ADR-006: Market Intelligence Cache and Prepared Data

**Status:** Implemented — Phase 1 + Phase 2 Live Snapshot

**Date:** 2026

### Context

Market intelligence computation must be efficient, restart-safe, and avoid redundant provider calls. The Phase 1 implementation establishes a persistent daily-bar store with specific caching semantics.

### Decision

Phase 1 implements the following cache and persistence model:

#### Persistent Daily-Bar Store
- Daily OHLCV bars persisted to SQLite via SQLAlchemy
- Upsert semantics: idempotent writes, safe to re-fetch
- Survives application restarts

#### Completed Daily Data Reuse
- Outside NSE market hours (pre-open to close), completed daily bars are **reused without re-fetch**
- Eliminates redundant provider calls for historical data
- Guarantees consistent indicators across requests within same trading day

#### Expiry Aligned to NSE Pre-Open
- Cache validity expires at the next NSE pre-open session (09:00 IST)
- Ensures fresh data at start of each trading day
- Aligns with market data availability cycle

#### Single-Flight Opportunity Computation
- Concurrent requests to `/api/opportunities` (or equivalent) are deduplicated
- Only one computation runs; waiters receive the same result
- Prevents thundering herd on provider APIs and CPU

#### Open-Market Behavior
- During market hours, today's forming bar is **not** in the daily-bar store
- Live quote/bulk quote provides current price/volume
- Intelligence overlays live data on completed history for real-time view
- Phase 2 optimizes this overlay with bulk quotes and efficient forming-bar handling

#### Phase 2 Separation — IMPLEMENTED / VALIDATED
- Phase 2 adds live snapshot layer on top of Phase 1 cache behavior
- Live snapshot caching with single-flight protection
- Forming-bar overlay during OPEN market; completed daily bars unchanged
- 32 deterministic Phase 2 tests validate the integration
- Phase 2 does not modify historical daily-bar persistence logic

### Future Work (PLANNED)
- Incremental historical refresh (backfill gaps without full re-fetch)
- Continuous/background intelligence refresh (prepared intelligence APIs)
- Multi-timeframe cache coordination

---

## Future ADRs

- ADR-007: Incremental Historical Refresh Strategy (PLANNED)
- ADR-008: Continuous Intelligence Architecture (PLANNED)
- ADR-009: Prepared Intelligence API Contract (PLANNED)
- ADR-010: Mobile Client Architecture (PLANNED)
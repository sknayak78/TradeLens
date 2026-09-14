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
- Easy provider replacement (Yahoo, Zerodha, Upstox, etc.)

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

The Recommendation Engine scored action, computed a pullback-style entry zone,
labelled a strategy afterwards, and built Watch Next from action + limits.
That produced contradictory cards — e.g. Strategy = Breakout with Entry Range =
buy 3294–3445 **and** Watch Next = wait for a close above 3485.

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

See `docs/ER-0016-STRATEGY-DRIVEN.md` for before/after examples.

---

## ADR-003: Market Data Provider Strategy — Upstox Primary with a Provider Chain

**Status:** Accepted

**Date:** 07-Sep-2026

**Request:** MD-02, MD-03

### Context

MD-02 proved Upstox historical OHLCV works behind the `MarketDataProvider`
boundary but left it unwired.  TradeLens needs a primary source that is
genuinely Indian-market native (latency, instrument master, LTP quotes); Yahoo
remains a capable secondary and the seeded dataset a deterministic last resort.
Wiring Upstox naively would have produced the same class of errors ADR-001
rejected — e.g. a "live" price that is actually a daily close, or indicators
mixed across providers.

### Decision

- The `MarketDataService` walks an ordered **provider chain** —
  `[Upstox, Yahoo, Seed]` when `MARKET_DATA_PROVIDER=upstox` is set.
  Providers are tried left to right; the first link gets two attempts, each
  later link one; a `NotImplementedError` catalogue op is a structural skip
  (no retry, no health flip); an **empty OHLCV** result (D4) falls through to
  the next provider.  The first successful provider's value is cached under the
  service cache key, like every other read.
- **Snapshot price semantics (D1):** for Upstox, the published `price` is the
  live LTP quote (`/v2/market-quote/ltp`) and is tagged `priceSource: "ltp"`.
  `changePct` is measured against the Upstox previous close.  All indicators
  (RSI, EMA20/50/200, VWAP, support/resistance), the insight, and the chart
  series derive from the **same** Upstox OHLCV dataset.  A daily close is never
  presented as a live price.
- **Catalogue metadata stays seeded:** `name`, `sector`, `dayHigh`,
  `avgVolume`, `score`, `trend` for catalogue symbols come from the seed
  catalogue (as provenance currently mandates).  Non-catalogue instruments
  resolved via the instrument master get neutral metadata (`sector: Equities`,
  `trend: neutral`, derived day-high/average volume).
- **Intraday guard (D3):** chart building rejects *intraday* bars only when
  they come from the synthetic `seed` provider; real intraday data from any
  real provider (Upstox or Yahoo) is accepted even when it is not the
  configured primary.  The daily fallback plan for an intraday timeframe stays
  allowed, so a fully seed-backed service can still render its labelled daily
  fallback.
- **Instrument master (deployment gate):** Upstox symbol resolution reads a
  versioned, bundled `NSE_EQ` instrument master
  (`backend/data/upstox_instruments.json`) that MUST pass validation — schema,
  `NSE_EQ` scope, required fields, symbol/key uniqueness, count consistency,
  generation metadata, and a **1500+ record** safety threshold.  `MARKET_DATA_
  PROVIDER=upstox` fails fast at startup on an invalid master; a placeholder or
  sample intentionally fails validation so it can never deploy.  The release
  artifact is produced by
  `scripts/fetch_upstox_instruments.py` and gated by
  `scripts/validate_upstox_instruments.py`.
- **LTP caching:** the LTP quote is read inside the provider's `get_stock`
  and is served through the same `MarketDataService` cache as every other op,
  so it can never bypass the configured TTL.
- **Component provenance:** stock-detail responses include additive
  `snapshotProvider`, `insightProvider`, and `chartProvider` fields because
  independent reads may legitimately degrade to different chain links.

### Consequences

Benefits

- Indian-native primary with a real instrument master instead of a curated map.
- Consistent single-source semantics per ADR-001: `priceSource: "ltp"` is
  truthful, and every indicator comes from one Upstox dataset.
- Deterministic degradation: Upstox outage → Yahoo → Seed, with the intraday
  guard keeping synthetic intraday bars off charts.
- A deploy gate that makes it impossible to ship a sample instrument master.

Trade-offs

- Snapshot reads now cost two Upstox calls (candles + LTP) on first fetch per
  TTL window; the service cache absorbs repeat reads.
- Upstox requires a release-time operator step to generate the instrument
  master (the CDN is not always reachable from build networks).
- Non-catalogue Upstox symbols carry neutral metadata until a licensed
  catalogue source is wired up.

---

## Future ADRs

- ADR-004 Technical Indicator Engine
- ADR-005 AI Decision Engine
- ADR-006 Paper Trading Architecture

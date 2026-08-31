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

## ADR-004: Technical Indicator Engine — One Authoritative EMA

**Status:** Accepted

**Date:** 31-Aug-2026

**Request:** ER-0038

### Context

TradeLens discovered a real user-visible EMA inconsistency on the Guided
Research screen (ER-0037): the chart EMA came from the selected timeframe's
candle series while the Quick Snapshot EMA came from an independently-computed
daily-2y series, so the two disagreed on intraday timeframes. ER-0037 made the
chart-series EMA authoritative for the chart and the Quick Snapshot.

On inspection there were **three** EMA implementations in the codebase:

1. `backend/services/chart_series.py` `compute_ema` — chart/research path.
2. `backend/indicators/ema.py` `calculate_ema`/`calculate_latest_ema` — daily
   snapshot / recommendation path.
3. `frontend/src/lib/candlestick.ts` `computeEMASeries` — frontend fallback.

Two of these produced different numeric behaviour because of different
warm-up/seed strategies, and one was an independent copy.

### Decision

**`backend/indicators/ema.py` is the single authoritative EMA module.** Every
backend consumer that needs an EMA value imports from here (directly or through
the `services.market_data.*` re-export barrels). No other module implements an
EMA on its own.

- `compute_ema(values, period)` is the **authoritative chart/research EMA**:
  emits `None` until `period` valid observations accumulate (seeded by their
  simple average), then smooths with the standard recursive formula
  `prev = value * k + (1 - k) * prev`, `k = 2 / (period + 1)`. It tolerates
  nullable/gapped inputs and never implies a value before warm-up.
- `calculate_ema`/`calculate_latest_ema` remain as the **daily-context** helpers
  (seed from the first value, emit from index 0) that the daily-2y recommendation
  snapshot uses. Their semantics were unchanged.
- `services/chart_series.py` now imports `compute_ema` from the indicators layer
  (re-exported for backward compatibility) instead of defining its own copy.
- `frontend/src/lib/candlestick.ts` `computeEMASeries` is retained **fallback-only**,
  applied via `pickFirst(backendValue, localValue)` so a valid backend EMA always
  wins; it is clearly documented as such.

Both variants implement the **same smoothing recurrence**; they differ only in
warm-up/seed strategy, which is an explicit **context parameter**, not a distinct
algorithm.

### What it owns

- The EMA20/50/200 series and latest-value calculations used across the product.

### What it does NOT own

- VWAP, Support/Resistance, RSI, recommendation scoring, or symbol normalization.
- Chart presentation, timeframe aggregation, or display-point construction — the
  chart layer orchestrates these and only *consumes* the EMA result.

### How timeframe context is supplied

Callers pass their own candle series (instrument + interval + continuous
history) and EMA period. The chart layer supplies the timeframe's fetch/aggregate
plan; the daily snapshot supplies its daily-2y series. Because EMA is context
driven by the supplied series, different contexts legitimately produce different
values without requiring separate algorithms.

### Why chart and recommendation EMA contexts may legitimately differ

The chart EMA is computed over the selected timeframe's candle interval (e.g.
intraday 5m/30m for 1D/1W); the recommendation EMA is computed over daily
candles for its analytical context. These are intentionally different series and
therefore different values — the goal is **one algorithm**, not one value for
every context.

### Consequences

- One place to reason about EMA behaviour; a future fix changes one file.
- Consumers cannot silently drift because there is no second copy to drift.
- Chart appearance, timeframe behaviour, recommendation scoring, and the daily
  snapshot payload are unchanged.
- The daily-context and chart-context functions coexist in one module; both are
  pinned by tests so their distinct warm-up semantics are preserved deliberately.

---

## Future ADRs

- ADR-003 Market Data Provider Strategy
- ADR-005 AI Decision Engine
- ADR-006 Paper Trading Architecture

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

## ADR-003: Future-Only Watch Next Triggers

**Status:** Accepted

**Date:** 07-Aug-2026

**Request:** ER-0018

### Context

Watch Next could instruct users to wait for a reclaim/break that the latest
price had already satisfied (e.g. price ₹1,326 watching reclaim of ₹1,300).

### Decision

Treat triggers as a finite state machine in `recommendation/triggers.py`:

- Validate every hurdle against `market.price` before publishing.
- Advance to the next logical future event (or a hold/cancel confirmation).
- Keep Trading Plan (`entry_condition`) on the same advanced thesis.

### Consequences

- Stale “wait for X” copy cannot ship when X has already happened.
- Recommendation, plan, and Watch Next stay consistent.

See `docs/ER-0018-TRIGGER-VALIDATION.md`.

---

## Future ADRs

- ADR-004 Market Data Provider Strategy
- ADR-005 Technical Indicator Engine
- ADR-006 AI Decision Engine
- ADR-007 Paper Trading Architecture

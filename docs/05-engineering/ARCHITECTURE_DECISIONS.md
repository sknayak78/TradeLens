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

See `docs/05-engineering/ER-0016-STRATEGY-DRIVEN-RECOMMENDATION-ENGINE.md`.

---

## ADR-003: Mentor Engine — Trading Setup vs Setup Progress

**Status:** Accepted

**Date:** 07-Aug-2026

### Context

Regenerating a full recommendation from today's close made TradeLens feel like a
daily signal machine: entry ceilings moved with the last print, risk/reward
drifted, and Watch Next could fight the plan. Mentors do not reinvent the setup
every session — they track progress against a plan.

### Decision

Split the engine into two layers:

```
score → structure → TradingSetup → SetupProgress → action → narrative
```

1. **Trading Setup** (stable while structure is stable)
   - Strategy, structural entry zone, stop, targets
   - Planned entry = midpoint of the structural zone
   - Risk/reward from planned entry — never from today's close
   - `structure_key` fingerprints EMA/S/R identity (excludes last price)

2. **Setup Progress** (updates with the session)
   - Status: ready / in_entry_zone / awaiting_entry / extended /
     breakout_pending / breakout_holding / invalidated / no_setup
   - Distances to entry / stop / target
   - Future-only `next_event` (feeds Watch Next)

Legacy `levels` / `strategy` / `action` / `nextTrigger` remain on the wire and
are derived from Setup + Progress. Additive `setup` and `progress` objects
expose the split explicitly.

Narrative sections stay non-repetitive: summary is context only; Watch Next is
owned by Progress.

### Consequences

- Quiet sessions cannot rewrite entry geometry or R:R.
- Action can soften from Strong Buy → Watch when price extends above the zone
  without changing the underlying setup.
- Breakout plans live on `setup.levels` while legacy `levels` stay null so the
  card never shows a buy-now zone under a wait-for-breakout thesis.
- Persistence of setups across days is a future step; within a snapshot, the
  stability contract is proven by holding structure fixed and varying price.

See `docs/05-engineering/MENTOR_ENGINE_SETUP_PROGRESS.md`.

---

## ADR-004: Insight v2 Educational Narrative Sections

**Status:** Accepted

**Date:** 07-Aug-2026

**Request:** ER-0020 (product: TradeLens Insight v2)

### Context

The Recommendation Card stacked Strengths / Key Reasons / Risks / beginner tip
with overlapping sentences (trend essay in both summary and why; stop-loss
invalidation repeated in risks and Watch Next). Mentors teach one idea at a
time.

### Decision

Each narrative field has a single purpose. New additive fields:

- `mentorLesson` — one strategy-keyed trading principle
- `whatWouldChangeMyView` — thesis invalidation in mentor voice
- `idealFor` — strategy audience ("Who is this setup for?")

Summary must not repeat the trend evidence used in `why`. Risks stay educational
and must not duplicate the stop-loss invalidation sentence owned by
`whatWouldChangeMyView`. Watch Next remains Progress-owned and operational.

### Consequences

- Card UI becomes a short mentor conversation instead of a three-column dump
- Regression tests enforce no identical prose across sections
- Existing v1.1 fields remain; Insight v2 fields are additive

See `docs/05-engineering/ER-0020-INSIGHT-V2-EDUCATIONAL-NARRATIVE.md`.

---

## Future ADRs

- ADR-005 Market Data Provider Strategy
- ADR-006 Technical Indicator Engine
- ADR-007 AI Decision Engine
- ADR-008 Paper Trading / Setup Persistence

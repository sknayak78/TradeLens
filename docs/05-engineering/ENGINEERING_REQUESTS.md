# TradeLens Engineering Requests

---

# Sprint 2 - Market Intelligence Engine

---

## ER-0004

### Title

Replace Seed Chart with Live Historical Market Data

### Priority

P0

### Status

Ready

### Business Goal

Ensure the chart always represents the same market data as the displayed live quote.

### Acceptance Criteria

- Fetch historical OHLCV data from Yahoo Finance.
- Replace seeded chart series.
- Keep API contract unchanged.
- Preserve provider abstraction.
- Preserve fallback to SeedProvider.
- Add unit tests.

---

## ER-0005

### Title

Technical Indicator Engine

### Priority

P0

### Status

Planned

### Deliverables

- EMA20
- EMA50
- EMA200
- RSI
- MACD
- ATR
- Bollinger Bands

---

## ER-0006

### Title

Analysis Engine

### Priority

P1

### Status

Planned

### Deliverables

Generate:

- Trend
- Strength Score
- Risk Level
- Suggested Action
- AI Explanation

---

## ER-0007

### Title

Developer Mode

### Priority

P2

### Status

Backlog

### Deliverables

Display:

- Active Provider
- Symbol Mapping
- Cache Status
- Response Time
- Data Quality
- Latest Candle Timestamp

---

## ER-0014

### Title

Recommendation Engine v1.1

### Priority

P0

### Status

Done

### Business Goal

Make the Recommendation Engine the authoritative, beginner-friendly answer to
"is this a good time to buy this stock today?".

### Deliverables

- Actions restricted to Strong Buy, Buy, Watch, Wait and Avoid; position
  management deferred to a future Portfolio Advisor.
- Additive fields: `strategy`, `verdict`, `summary`, `why[]`, `positives[]`,
  `risks[]`, `nextTrigger`, `beginnerTip`, `idealFor`.
- Trading strategy (Fresh Entry, Pullback, Breakout, No Entry Yet) exposed as
  `strategy` so the action stays a pure decision.
- Plain-English explanations in place of indicator readings.
- Confidence banded per action and never 100%.
- Holding period always a trade duration, never a status.
- Legacy fields retained but excluded from recommendation logic.
---

## ER-0014A

### Title

Recommendation Logic Calibration

### Priority

P0

### Status

Done

### Business Goal

Stop the engine from writing off healthy stocks that are simply having a bad
week, and keep the narrative honest about what the indicators actually show.

### Deliverables

- Trend derived from EMA20/EMA50/EMA200 read together: while the price holds
  its long-term average a dip under the shorter averages is a pullback.
- `Avoid` reserved for a broken trend; a pullback is at worst a `Wait`,
  however thin today's evidence is.
- Narrative claims tied to available indicators: no "buyers are in control" or
  "selling interest is weak" without support, and no long-term claims when the
  long-term average is missing.

---

## ER-0014B

### Title

Establish Recommendation as the Single Source of Truth

### Priority

P0

### Status

Done

### Business Goal

Make the API expose exactly one trading opinion, so a parent `trend`/`score` can
never disagree with the `recommendation` block beneath it.

### Deliverables

- `services/stock_decision.decide()` is the only source of a published trend or
  score; stock detail, watchlist, rankings and the catalog all read it.
- Seeded `trend`/`score` literals are no longer served anywhere.
- `vwap` recomputed from live bars as a rolling 20-session VWAP
  (`indicators/vwap.py`) instead of carrying a seeded value from another era.
- Legacy analysis fields (`suggestedAction`, `classification`, `insight`,
  `tradeSetup`, `riskLevel`, `strengthScore`, `stars`) marked deprecated in the
  schema; retained on the wire and still not inputs to the engine.
- Field-by-field provenance and the migration plan documented in
  `docs/DATA_PROVENANCE.md`.

---

## ER-0016

### Title

Strategy-Driven Recommendation Engine

### Priority

P0

### Status

Done

### Business Goal

Every recommendation represents exactly one trading thesis. Strategy is the
parent decision so Entry, Stop, Targets, Watch Next and narrative can never
contradict each other.

### Deliverables

- Strategy classified before action and before levels are published.
- Levels published only for Trend Continuation and Pullback.
- Breakout / Consolidation / No Entry Yet never publish a buy-now entry range.
- Narrative receives strategy and derives Watch Next / entry condition from it.
- Strategy vocabulary: Trend Continuation (was Fresh Entry), Pullback, Breakout,
  Consolidation, No Entry Yet.
- Consistency tests for Breakout, Pullback, Trend Continuation, Consolidation,
  Avoid.
- Architecture notes in `docs/ER-0016-STRATEGY-DRIVEN.md` and ADR-002.

---

## ER-0019

### Title

Mentor Engine — Trading Setup vs Setup Progress

### Priority

P0

### Status

Done

### Business Goal

Refactor the recommendation engine into a Mentor Engine that tracks a stable
Trading Setup while daily price only updates Setup Progress.

### Deliverables

- Structure fingerprint + structure-based entry zones
- R:R from planned entry (zone midpoint), never today's close
- Setup Progress statuses and future-only Watch Next
- Additive `setup` / `progress` API fields
- Regression tests for all strategies + setup stability
- ADR-003 and `MENTOR_ENGINE_SETUP_PROGRESS.md`

---

## ER-0020

### Title

TradeLens Insight v2: Educational Narrative

### Priority

P0

### Status

Done

### Business Goal

Replace repetitive recommendation narrative with a concise educational mentor
conversation that teaches one trading principle per insight.

### Deliverables

- Mentor's Lesson / What would change my view? / Who is this setup for?
- Non-repetitive narrative assembly (`insight.py` + narrative refactor)
- Concise Recommendation Card mentor UI
- Regression tests for section uniqueness
- ADR-004 and `ER-0020-INSIGHT-V2-EDUCATIONAL-NARRATIVE.md`

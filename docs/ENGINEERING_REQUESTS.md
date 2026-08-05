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
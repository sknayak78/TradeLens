# TradeLens Product Roadmap

> Vision: Build the most trusted AI-assisted trading platform for novice Indian traders.

---

# Version 1.1 (Completed)

## Market Data

- ✅ Provider Architecture
- ✅ Yahoo Finance Integration
- ✅ Automatic Seed Fallback
- ✅ Developer Toolkit
- ✅ Local Development Environment
- ✅ Watchlist
- ✅ Dashboard
- ✅ AI Insight (Prototype)

---

# Version 2.0 (Current Sprint)

## Sprint 2A – Market Data Engine

- [x] Live Historical OHLCV Data
- [x] Live Chart
- [x] Provider Metadata
- [x] Better Error Logging
- [x] Data Quality Validation

---

## Current Market Data Engineering State

The market-data engine is further along than the Sprint 2A checklist alone
suggests. The MD-series stories and their current state:

| Story | Scope | Commit | State |
| --- | --- | --- | --- |
| MD-04 | Market scanner | — | Implemented · Committed · Pushed |
| MD-05 | Opportunity ranking | — | Implemented · Committed · Pushed |
| MD-06 | Opportunity explainability | — | Implemented · Committed · Pushed |
| MD-07 | Deep analysis pipeline | — | Implemented · Committed · Pushed |
| MD-08 | Today's opportunities (broad discovery + curated fallback) | `59e54ea`, `e7fb859`, `0568b86` | Implemented · Committed · Pushed |
| MD-08/10 | Upstox rate limits (bounded retry) | `1f00bcf` | Implemented · Committed · Pushed |
| MD-10 | Bulk market discovery (canonical bulk-quote path) | `33499de` | Implemented · Committed · Pushed |
| MD-11 Phase 1 | Single-flight opportunity discovery | `3c18845` | Implemented · Committed · Pushed |
| MD-11 Phase 2 | Forming daily-bar overlay | `a96240f` | Implemented · Committed · Pushed |
| MD-11 Phase 3 | `DailyBarStore` integration into the daily-bar read path | — | **Planned / Not started** |
| — | Supported Python runtime baseline | `39996e1` | Implemented · Committed · Pushed |

Authoritative detail lives in the per-story documents:

- `docs/05-engineering/MD-08-TODAYS-OPPORTUNITIES.md`
- `docs/05-engineering/MD-10-BULK-MARKET-DISCOVERY.md`
- `docs/05-engineering/MD-11-DAILY-BAR-READ-PATH.md`
- `docs/05-engineering/ARCHITECTURE_DECISIONS.md` (ADR-001 … ADR-004)
- `docs/05-engineering/DATA_PROVENANCE.md`

**Next step.** MD-11 Phase 3 — wire the existing `DailyBarStore` into the
historical daily-bar read path. It is an integration of an already-implemented
store, not a new cache, and must not alter the MD-10 bulk architecture, the
Phase 1 single-flight guard, or the Phase 2 forming-bar overlay.

**Developer prerequisite.** The backend supports Python `>=3.12,<3.14`, with
3.12 as the validated default. Python 3.14 is not supported because
`SQLAlchemy==2.0.36` cannot be imported there. See the "Python runtime"
section of the repository `README.md`.

---

## Sprint 2B – Technical Indicator Engine

- [ ] EMA
- [ ] RSI
- [ ] MACD
- [ ] ATR
- [ ] Bollinger Bands
- [ ] Support & Resistance

---

## Sprint 2C – Analysis Engine

- [ ] Trend Analysis
- [ ] Strength Score
- [ ] Trading Setup Detection
- [ ] Risk Assessment

---

## Sprint 2D – AI Trading Coach

- [ ] Explain Every Indicator
- [ ] Explain Every Trade
- [ ] Beginner Mode
- [ ] Educational Insights

---

# Version 3.0

## Trading

- [ ] Paper Trading
- [ ] Portfolio Tracker
- [ ] Trading Journal
- [ ] Performance Analytics

---

# Version 4.0

## Professional Platform

- [ ] Zerodha Integration
- [ ] Upstox Integration
- [ ] Dhan Integration
- [ ] Real-time Streaming
- [ ] Mobile App

---

# Long-Term Vision

TradeLens will become an AI-powered trading companion that helps users:

- Learn trading
- Analyze markets
- Practice with paper trading
- Build discipline
- Transition to live trading confidently

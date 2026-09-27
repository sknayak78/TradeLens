# TradeLens Mentor Engine Specification

> "The Mentor Engine is the brain of TradeLens. It does not predict the market; it teaches users how to think about it."

Version: 0.1

Status: Draft

Owner: Product

---

# Table of Contents

1. Purpose
2. Vision
3. Design Philosophy
4. Core Principles
5. The Mentor Thinking Process
6. Market State Model
7. Strategy Selection
8. TradeLens Insight Generation
9. Mentor Challenge
10. AI Mentor
11. Practice Portfolio
12. Learning Framework
13. User Transformation
14. Future Evolution
15. Current Implementation Status

# TradeLens Mentor Engine Specification

> "The Mentor Engine is the brain of TradeLens. It does not predict the market; it teaches users how to think about it."

Version: 0.1

Status: Draft

Owner: Product

---

# Table of Contents

1. Purpose
2. Vision
3. Design Philosophy
4. Core Principles
5. The Mentor Thinking Process
6. Market State Model
7. Strategy Selection
8. TradeLens Insight Generation
9. Mentor Challenge
10. AI Mentor
11. Practice Portfolio
12. Learning Framework
13. User Transformation
14. Future Evolution
15. Current Implementation Status

## Vision

TradeLens is not building another recommendation engine.

TradeLens is building an AI Trading Mentor.

The Mentor Engine should behave like an experienced trader sitting beside the user.

It should:

- Observe
- Analyze
- Explain
- Challenge
- Teach
- Encourage patience
- Build confidence

The engine should never encourage blind following.

Its goal is to create independent traders.


## Design Philosophy

The Mentor Engine follows six principles.

### 1. Teach Before You Recommend

Explanation comes before action.

---

### 2. One Insight = One Thesis

Every section supports one coherent conclusion.

No contradictions.

---

### 3. Evidence Before Opinion

Every conclusion must be supported by observable market evidence.

---

### 4. Patience Over Activity

The best trade is often waiting.

The Mentor should celebrate patience.

---

### 5. Risk Before Reward

Every opportunity begins with downside analysis.

---

### 6. Confidence Through Understanding

Users should trust their own reasoning more every week.


Market Data
        │
        ▼
Indicator Engine
        │
        ▼
Market Context
        │
        ▼
Market State
        │
        ▼
Strategy Selection
        │
        ▼
TradeLens Insight
        │
        ▼
Mentor Challenge
        │
        ▼
Mentor Feedback
        │
        ▼
Practice Portfolio
        │
        ▼
Learning Analytics
        │
        ▼
User Growth

## Inputs

The Mentor Engine consumes multiple layers of information.

### Market Data

- Price
- Volume
- OHLC

### Trend

- EMA20
- EMA50
- EMA200

### Momentum

- RSI

### Structure

- Support
- Resistance

### Volatility

- ATR

### Relative Strength

Future

### Sector Performance

Future

### Market Breadth

Future

### User History

Future

### Practice Portfolio

Future

### Mentor Challenges

Future


## Outputs

The Mentor Engine does not produce recommendations.

It produces TradeLens Insights.

Each insight contains:

- Market Context
- Strategy
- Trading Plan
- Strengths
- Risks
- Watch Next
- Educational Guidance

Future

- Mentor Challenge
- AI Discussion
- Trade Review

## Mentor Challenge

Before revealing the Mentor's conclusion,
the user should be encouraged to think independently.

Question:

"What would you do?"

Possible responses:

- Ready
- Prepare
- Pass

Only after the user commits should the Mentor reveal its reasoning.

Learning happens through comparison, not imitation.

## Practice Portfolio

The Practice Portfolio exists for education.

It is not a trading simulator.

Users receive virtual capital.

Every decision is recorded.

Every trade becomes a learning opportunity.

Every completed trade receives Mentor Feedback.


## Learning Framework

Observe

↓

Understand

↓

Think

↓

Decide

↓

Commit

↓

Compare

↓

Reflect

↓

Improve



Not



Recommendation

↓

Buy

Huge difference.


## Success Metrics

TradeLens does not measure success by:

- Trades executed
- Daily active users
- Notification clicks

Instead, the Mentor Engine measures:

- Better decision quality
- Improved patience
- Better risk management
- Increased confidence
- Growth in trading knowledge

## User Transformation
Beginner

↓

Curious Learner

↓

Confident Learner

↓

Disciplined Trader

↓

Independent Trader

↓

Mentor to Others

## Future Evolution

The Mentor Engine will evolve through multiple stages.

### Stage 1

Market Analysis

### Stage 2

TradeLens Insight

### Stage 3

Mentor Challenge

### Stage 4

Practice Portfolio

### Stage 5

AI Trade Reviews

### Stage 6

Personalized Coaching

### Stage 7

Behavioral Analysis

### Stage 8

Daily Trading Mentor

---

## Current Implementation Status

### Stage 1 — IMPLEMENTED: Market Analysis
- Persistent daily-bar store (OHLCV) with restart-safe persistence
- Technical indicators: EMA 20/50/200, RSI, VWAP (rolling 20-session), Support/Resistance, ATR
- Provider-neutral normalized market data via adapter pattern
- Upstox and Yahoo Finance adapters implemented

### Stage 2 — IMPLEMENTED: TradeLens Insight
- Discovery: Universe filtering, ranking by momentum/structure/volume
- Deep Analysis: Per-symbol EvidenceBundle (trend, momentum, structure, volatility, risk/reward)
- TradeLens Score: Deterministic 0-100 composite from evidence (no LLM in scoring path)
- Strategy-driven recommendations: Trend Continuation, Pullback, Breakout, Consolidation, No Entry Yet
- Strategy is parent decision (ADR-002): levels and narrative derived from strategy
- Recommendation Engine v1.1: Single source of truth (ADR-001, ER-0014B)
- AI synthesis layer: Explains evidence and score; never overrides authoritative score (ADR-005)

### Stages 3-8 — PLANNED
| Stage | Capability | Status |
|-------|------------|--------|
| 3 | Mentor Challenge (user decision before reveal) | PLANNED |
| 4 | Practice Portfolio (virtual capital, decision recording) | PLANNED |
| 5 | AI Trade Reviews | PLANNED |
| 6 | Personalized Coaching | PLANNED |
| 7 | Behavioral Analysis | PLANNED |
| 8 | Daily Trading Mentor | PLANNED |

### Architecture Clarification

The **deterministic intelligence pipeline** (Market Data → Indicators → Evidence → TradeLens Score) is the authoritative analysis path.

**AI is a synthesis/explanation layer** that receives the deterministic score and evidence, then produces natural-language narrative, educational guidance, and "watch next" triggers. AI never calculates, influences, or overrides the TradeLens Score.

This separation is enforced by architecture (ADR-004, ADR-005) and validated by regression tests (PROV-008, PROV-009, PROV-010).

### Provider Neutrality

The Mentor Engine consumes normalized market data only. It has no knowledge of Upstox, Yahoo, HDFC, or any specific provider. Provider adapters (ADR-003) handle authentication, API quirks, and data normalization.

### Read-Only Scope

Initial provider integrations are READ-ONLY for market research and intelligence. Order execution is NOT in scope. The Mentor Engine produces insights and trade plans — not executable orders.

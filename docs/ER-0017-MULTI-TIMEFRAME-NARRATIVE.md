# ER-0017 — Multi-Timeframe Narrative Intelligence

## Problem

This is a **communication** problem, not a calculation problem.

A stock can rise for several sessions while still sitting below its long-term
average. The engine correctly calls that **Avoid**, but the old narrative said
only “the downtrend can continue…” — which felt like it contradicted the chart
a beginner was staring at.

## Design

Keep the Recommendation Engine decision unchanged. Add a pure
`TimeframeContext` (`recommendation/timeframe.py`) that labels structure:

| Structure | Meaning |
| --- | --- |
| `aligned_bullish` | Short and long horizons agree up |
| `aligned_bearish` | Short and long horizons agree down |
| `pullback` | Long-term up, short-term soft |
| `counter_trend_rally` | Long-term down, short-term lifting |
| `consolidation` | Mixed / unclear |
| `insufficient` | Not enough averages |

Narrative sections each answer one question and must not repeat:

| Field | Question |
| --- | --- |
| `verdict` | What should I do today? |
| `summary` | What am I seeing on the chart? |
| `why` | What is the evidence? |
| `risks` | What could go wrong? |
| `entry_condition` | How should I execute? |
| `next_trigger` | When should I revisit? |

## Before / after

### Counter-trend rally (the reported bug)

**Setup:** Price 95, recent average 90, long-term average 110 → chart rising, structure still bearish.

**Before**

- Summary: “The price has lost its long-term average… rallies are likely to be sold into.”
- Risks: “The downtrend can continue far longer than it looks like it should.”
- Watch Next: “Reclaim its recent average price of 90” *(price is already above 90)*

**After**

- Verdict: Stay out — recent bounce looks like a counter-trend rally.
- Market context: Acknowledges the multi-session recovery **and** explains the broader trend is still bearish below 110; names “counter-trend rally”.
- Watch Next: Daily close back above the **long-term** average of 110.
- Risks: Explain why buying the bounce traps beginners.

### Bullish continuation

- Context teaches that short-term and long-term **agree**.
- Entry prices live in Trading Plan, not repeated as the whole summary.

### Pullback

- “Long-term uptrend despite the recent short-term pullback.”

### Breakout

- Teaches breakout confirmation; Watch Next stays “close above resistance”.

### Consolidation

- Mixed signals → patience until direction returns.

### Avoid (aligned bearish)

- Names the long-term downtrend without denying any short bounce (none present).

## API

No public field changes. Additive teaching language only.

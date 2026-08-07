# ER-0016 — Strategy-Driven Recommendation Engine

## Root-cause analysis

### Pipeline before ER-0016

```
score → trend → levels (always pullback geometry) → limits → action
                                                      ↓
                                              strategy (label only)
                                                      ↓
                                              narrative(action, limits, levels)
```

| Field | Where created | Problem |
| --- | --- | --- |
| Strategy | `engine._strategy()` — **after** action/levels | Late label; does not control levels or prose |
| Entry range | `engine._levels()` — always `max(EMA20, support) → price` | Same geometry for every non-Avoid call, including Breakout |
| Watch Next | `narrative._next_trigger()` — branches on action + limits | Breakout path says “wait for close above resistance” |
| Narrative | `narrative.build()` — never receives strategy | Cannot keep prose aligned with the thesis |

### Why the contradiction appears

For a stock pressed under resistance (`Watch` + thin headroom):

1. `_levels()` still publishes a **buy-now** zone below the last price (e.g. 3294–3445).
2. `_strategy()` labels the call **Breakout**.
3. `_next_trigger()` independently says **wait for a daily close above resistance** (e.g. 3485).

The card therefore shows two theses: “buy here” and “wait for breakout.”

### Architectural fix (smallest change)

Make **strategy the parent decision**. Everything else is derived from it:

```
score → trend → candidate zone → limits → STRATEGY
                                           ↓
                         action · published levels · narrative · risks
```

Rules:

- One recommendation = one strategy = one trading thesis.
- Levels are published only when the strategy’s thesis includes a buy zone today
  (`Trend Continuation`, `Pullback`).
- Breakout / Consolidation / No Entry Yet never publish a buy-now entry range.
- Narrative receives `strategy` and writes Watch Next / entry condition / summary
  from that thesis alone.

### Strategy vocabulary (necessary API tweak)

| Before | After | Role |
| --- | --- | --- |
| Fresh Entry | **Trend Continuation** | Enter with the trend today |
| Pullback | Pullback | Wait for price to come into the zone |
| Breakout | Breakout | Wait for confirmed break of resistance |
| *(none)* | **Consolidation** | Range / unclear; no entry plan |
| No Entry Yet | No Entry Yet | Stay out (including Avoid) |

`Fresh Entry` → `Trend Continuation` is a deliberate rename: “Fresh Entry” described
timing, not a trading strategy. Frontend and schema literals are updated in the
same change. No other public fields move.

## Before / after

### Breakout (the reported bug)

**Before**

- Strategy = Breakout
- Entry Range = Buy between 3294–3445
- Watch Next = Wait for daily close above 3485

**After**

- Strategy = Breakout
- Levels = `null` (no buy-now entry)
- Entry condition / Watch Next = Wait for a daily close above 3485
- Verdict / summary reinforce “not today — wait for the break”

### Pullback

- Strategy = Pullback
- Levels = buy zone (on the pullback)
- Watch Next = Wait for the pullback into that zone
- Never asks for a breakout confirmation as the primary next step

### Trend Continuation

- Strategy = Trend Continuation
- Levels = buy-now zone with stop and targets
- Watch Next = Manage the stop / targets of the open plan

### Consolidation

- Strategy = Consolidation
- Levels = `null`
- Watch Next = Wait for the range to resolve into a clear direction

### Avoid

- Action = Avoid, Strategy = No Entry Yet
- Levels = `null`
- Watch Next = Wait for buyers to reclaim the trend

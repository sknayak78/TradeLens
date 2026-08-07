# Mentor Engine — Trading Setup vs Setup Progress

## Goal

Behave like an experienced mentor who tracks a setup over time, instead of
minting a new recommendation every time the last price ticks.

## Split

| Layer | Owns | Changes when |
| --- | --- | --- |
| **Trading Setup** | Strategy, structural entry zone, stop, targets, planned entry, R:R | Market **structure** changes (EMAs / S/R) |
| **Setup Progress** | Status, distances, Watch Next | **Today's price** moves |

## Geometry rules

- Entry zone floor = `max(EMA20, support)` (structure)
- Entry zone ceiling = floor + structural band (share of S/R span) — **not** last close
- Planned entry = midpoint of that zone
- Risk/reward = `(target1 − planned_entry) / (planned_entry − stop)`

## Pipeline

```
score → structure → TradingSetup → SetupProgress → action → narrative
```

## API

Additive fields on `recommendation`:

- `setup` — `{ strategy, trend, structureKey, plannedEntry, levels, score }`
- `progress` — `{ status, price, distanceToEntryPct, distanceToStopPct, distanceToTarget1Pct, nextEvent }`

Legacy fields remain and are derived from the same objects.

## Example

Same structure, price 110 → 112:

| | Day 1 (110) | Day 2 (112) |
| --- | --- | --- |
| Setup strategy | Trend Continuation | Trend Continuation |
| Entry / R:R | Unchanged | Unchanged |
| Progress | `ready` | `extended` |
| Action | Strong Buy | Watch |
| Watch Next | In-zone invalidation | Pullback toward zone |

## Modules

- `recommendation/structure.py`
- `recommendation/setup.py`
- `recommendation/progress.py`
- `recommendation/engine.py` (orchestrator)

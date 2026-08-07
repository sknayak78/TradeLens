# ER-0018 — Trigger Validation & State Consistency

## Problem

Watch Next could ask the trader to wait for an event that had **already
happened** at the latest price.

**Example**

- Current price = ₹1,326.30
- Watch Next = “Watch for price to reclaim ₹1,300.16”

The reclaim was already satisfied. That destroys trust.

## Root cause

`_next_trigger` / `_entry_condition` emitted template text from strategy alone
and never checked whether the quoted level was still in the future relative to
`market.price`.

## Fix

New pure module `recommendation/triggers.py`:

1. Model a `Trigger` (level + direction: above / below / toward).
2. Build a reclaim chain: short → medium → long average → resistance.
3. Skip any hurdle the latest price has already cleared.
4. If every reclaim is done, advance to a **hold / cancel** confirmation.
5. Same rules drive Trading Plan (`entry_condition`) so plan and Watch Next
   stay on one thesis.

| Prior state | If already satisfied → next |
| --- | --- |
| Reclaim short average | Next higher average / resistance, else hold-above |
| Breakout above resistance | Hold confirmation / fail-back cancel |
| Pullback into zone | Pull toward zone floor; if at floor → stop invalidation |
| Target 1 cleared (Trend Continuation) | Extend toward target 2 |

## Before / after (reported bug)

**Before:** Watch for reclaim of 1,300.16 (already held at 1,326.30)  
**After:** Watch for price to **hold above** 1,300.16; a slip back cancels progress

## API

No public field changes.

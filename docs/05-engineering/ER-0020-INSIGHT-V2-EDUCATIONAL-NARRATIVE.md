# ER-0020 — TradeLens Insight v2: Educational Narrative

**Product title:** TradeLens Insight v2: Educational Narrative  
**Engineering id:** ER-0020  
*(ER-0019 is Mentor Engine — Setup vs Progress.)*

## Objective

Transform the TradeLens Insight from a recommendation card dump into an
educational mentor conversation: every insight teaches at least one trading
principle, and no section repeats another.

## Pipeline (unchanged)

```
score → structure → TradingSetup → SetupProgress → action → narrative
```

Insight v2 extends **narrative** only. Setup / Progress remain the source of
truth for levels and Watch Next.

## Section purposes

| Section | Purpose |
|---|---|
| Verdict | One-line decision |
| Summary | Conversational opening — what to do now |
| Mentor's Lesson | One trading principle for this strategy |
| Trading Plan | How to execute |
| Why this call | Evidence (compact) |
| Risks to respect | What can go wrong (general education) |
| What would change my view? | Thesis invalidation |
| Who is this setup for? | Audience fit (strategy-keyed) |
| Watch Next | Future operational event (from Progress) |

`beginnerTip` remains on the API (action-keyed practice tip) for compatibility;
the card surfaces Mentor's Lesson instead of duplicating "what next" copy.

## Additive API

```json
{
  "mentorLesson": "...",
  "whatWouldChangeMyView": "...",
  "idealFor": "..."
}
```

`idealFor` now mirrors strategy audience (`who_is_this_for`) so "Who is this
setup for?" matches the thesis. Legacy action-keyed `IDEAL_FOR` remains in
config for reference but is no longer wired into recommendations.

## Files

- `backend/recommendation/insight.py` — lessons, audience, change-view copy
- `backend/recommendation/narrative.py` — non-repetitive assembly
- `frontend/.../RecommendationCard.tsx` — mentor conversation UI
- `backend/tests/test_insight_narrative.py` — consistency regressions

## Acceptance

- [x] No repeated information across sections
- [x] Every insight teaches ≥1 trading principle
- [x] Users understand both what to do and why
- [x] UI stays concise (quality over quantity)

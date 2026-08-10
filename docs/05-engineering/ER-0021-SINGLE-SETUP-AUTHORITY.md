# ER-0021 — Single Setup Authority

**Status:** Implemented  
**Depends on:** ER-0019 (Mentor Engine), ER-0020 (Insight v2)

## Problem

Stock detail and Today's Opportunities could disagree on Setup / Action because
they read different classifiers:

1. **Recommendation Card / Chart (after ER-0021)** → `recommendation.action` /
   `recommendation.strategy`
2. **Today's Opportunities (before rankings extension)** → legacy
   `suggestedAction` / `tradeSetup` from `StockAnalysisService`

Separately, **Trading Plan** (`entryCondition`) was derived from strategy alone
and ignored `SetupProgress.status`.

## Decision

| Surface | Authority |
| --- | --- |
| Suggested Action (ChartCard) | `recommendation.action` when present; else legacy |
| Setup badge (ChartCard) | `recommendation.setup.strategy` ?? `recommendation.strategy`; else legacy |
| Opportunities Setup | Ranking.`strategy` (mentor); else `tradeSetup` |
| Opportunities Action | Ranking.`action` (mentor); else `suggestedAction` |
| Trading Plan | `narrative._entry_condition` **with** `SetupProgress.status` |
| Watch Next | unchanged — already `progress.next_event` |
| Legacy API fields | retained on the wire (`tradeSetup`, `suggestedAction`) |

`GET /api/opportunities` reuses the existing per-row `decide(stock)` call — it
does **not** invoke the Mentor Engine twice and does not embed full
`RecommendationOut` on each Ranking row.

Breakout strategy must **never** be displayed as current action
`BUY ON BREAKOUT`. Confirmation stays in Watch Next / Trading Plan triggers.

## Non-goals

- No change to scoring, strategy classification, R:R thresholds, or
  `action_from_progress()`.
- No change to rankings sort key (`strengthScore`).
- In-zone Pullback with poor R:R remains **WATCH** (patience), not BUY.

## Files

- `backend/recommendation/narrative.py` — progress-aware Trading Plan
- `backend/schemas.py` / `backend/routers/market.py` — Ranking `action`/`strategy`
- `frontend/src/components/panels/stockDetailAuthority.ts` — chart + rankings selectors
- `frontend/src/components/panels/ChartCard.tsx` / `TopOpportunities.tsx`
- `frontend/src/components/panels/AnalysisBadges.tsx` — accept strategy labels
- `backend/tests/test_er_0021_single_setup_authority.py`
- `frontend/src/components/panels/stockDetailAuthority.test.ts`

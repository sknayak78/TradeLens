# TradeLens — Master Regression Suite

**Status:** Living regression baseline  
**Purpose:** Preserve functional, analytical, UX, data-integrity, and learning-system behavior across future ERs.  
**Maintenance rule:** Every new ER should add or update regression cases here. Do not remove a test merely because an implementation changes; first document the replacement behavior and its rationale.

---

## 1. Regression Philosophy

TradeLens is not just a charting application. Its core trust chain is:

**Market data → indicators/levels → recommendation engine → explanation → user decision → Mentor comparison → learning outcome → journal/watchlist**

Regression testing must therefore protect:

1. **Numerical correctness** — prices, OHLCV, EMA, RSI, VWAP, support/resistance.
2. **Temporal correctness** — timeframe, aggregation, historical lookback, X-axis semantics.
3. **Recommendation correctness** — strategy, action, confidence/evidence strength, levels, risks, rationale.
4. **Single source of truth** — Dashboard, Stock Detail, Watchlist, Guided Research and Mentor surfaces must not disagree.
5. **Learning integrity** — user decision must be captured before Mentor reveal.
6. **Trading workflow integrity** — Watchlist and Trade Journal actions must persist correctly.
7. **UI readability** — charts must remain legible at supported widths and timeframes.
8. **Data provenance / anti-look-ahead** — historical analysis must not accidentally use future information.
9. **Backward compatibility** — existing API contracts and legacy consumers must remain stable unless an ER explicitly changes them.
10. **Determinism** — recommendation logic must not depend on clock, randomness, network or LLM calls.

---

# 2. P0 — Critical Smoke / Release Gate

These are mandatory before considering a build release-ready.

| ID | Area | Test | Expected |
|---|---|---|---|
| P0-01 | App | Launch frontend + backend | Application loads without fatal errors |
| P0-02 | Dashboard | Open default dashboard | Stock, price, recommendation and chart render |
| P0-03 | Chart | Switch 1D / 1W / 1M / 3M / 1Y | Each timeframe renders correct data without crash |
| P0-04 | Chart | Hover candlestick | OHLCV + EMA values render and are internally consistent |
| P0-05 | Recommendation | Compare recommendation across Dashboard and Stock Detail | Same authoritative recommendation |
| P0-06 | Guided Research | Complete Study → Decide → Compare → Learn | Mentor remains hidden until decision; reveal works afterward |
| P0-07 | Watchlist | Add stock | Stock appears in Watchlist and duplicate add is prevented |
| P0-08 | Journal | Add trade from researched stock | Journal dialog is prefilled with correct symbol |
| P0-09 | Journal | Save/edit/delete trade | Persistence and displayed values remain correct |
| P0-10 | API | Core market/recommendation endpoints | No unexpected 4xx/5xx responses |
| P0-11 | Build | Production frontend build | Build succeeds |
| P0-12 | Tests | Full automated regression suite | No new failures versus approved baseline |

---

# 3. P0 — Recommendation Engine & Mentor Trust

## 3.1 Single Source of Truth

- **REC-001:** Dashboard recommendation equals `decide()` result.
- **REC-002:** Stock Detail recommendation equals `decide()` result.
- **REC-003:** Watchlist recommendation equals `decide()` result.
- **REC-004:** Guided Research recommendation uses the same authoritative decision.
- **REC-005:** No UI surface independently recalculates recommendation fields.
- **REC-006:** Legacy recommendation fields remain served while consumers still depend on them.
- **REC-007:** Strategy, action, levels and narrative remain mutually consistent.

## 3.2 Strategy / Action Consistency

- **REC-010:** One recommendation has one parent strategy/thesis.
- **REC-011:** Action is valid for the selected strategy.
- **REC-012:** Strong Buy / Buy / Watch / Wait / Avoid thresholds behave exactly as configured.
- **REC-013:** Recommendation never claims a stronger action when a strategy limit blocks it.
- **REC-014:** Pullback strategy does not produce a contradictory immediate-entry message.
- **REC-015:** Trend Continuation does not produce a pullback contradiction.
- **REC-016:** Missing levels are handled safely.
- **REC-017:** Partial data downgrades recommendation appropriately.
- **REC-018:** RSI overbought/oversold conditions generate the correct risk/warning behavior.
- **REC-019:** Poor risk/reward prevents an unjustifiably strong call.
- **REC-020:** Price at/above resistance is treated as a meaningful entry constraint.

## 3.3 Confidence / Evidence Strength

- **REC-030:** Numeric value stays within configured bounds.
- **REC-031:** Confidence/evidence strength is never presented as probability of profit.
- **REC-032:** UI explanatory hint states that it reflects strength of supporting evidence.
- **REC-033:** Thresholds remain deterministic.
- **REC-034:** Confidence is not described as historically calibrated unless calibration exists.
- **REC-035:** Any future calibration must be validated against stored historical snapshots, not current dynamic indicators.

---

# 4. P0 — Data, Indicators & Chart Integrity

## 4.1 OHLCV

- **CHART-001:** Open, High, Low, Close and Volume are mapped to the correct candle.
- **CHART-002:** High ≥ max(Open, Close).
- **CHART-003:** Low ≤ min(Open, Close).
- **CHART-004:** Candle chronology is ascending.
- **CHART-005:** No duplicate timestamps.
- **CHART-006:** Missing/partial market data is surfaced rather than silently fabricated.

## 4.2 EMA

- **CHART-010:** EMA20 is calculated from sufficient historical lookback beyond the visible window.
- **CHART-011:** EMA50 is calculated from sufficient historical lookback.
- **CHART-012:** EMA200 is calculated from sufficient historical lookback.
- **CHART-013:** Changing timeframe does not incorrectly reset EMA history.
- **CHART-014:** EMA hover value matches the plotted EMA for the same candle.
- **CHART-015:** Quick Snapshot EMA values correspond to the same authoritative market snapshot as the chart.
- **CHART-016:** EMA values are not accidentally calculated from the currently visible subset only.
- **CHART-017:** EMA behavior remains correct when historical data count is near the minimum required lookback.

## 4.3 RSI / VWAP / Levels

- **CHART-020:** RSI uses the intended 14-period calculation.
- **CHART-021:** VWAP uses the intended session/lookback semantics.
- **CHART-022:** Support and resistance use the intended rolling window.
- **CHART-023:** Current price is not substituted for historical values when calculating structural levels.
- **CHART-024:** Indicator labels and displayed values use the same snapshot.
- **CHART-025:** No future candle is used in a historical indicator calculation.

---

# 5. P0 — Timeframe & X-Axis Regression

This section exists because repeated testing uncovered real X-axis failures.

## 5.1 1D

- **AXIS-001:** First meaningful intraday label starts at/near the market open (expected 09:15 for NSE data), not a late-session label such as 14:50.
- **AXIS-002:** Early labels do not disappear simply because the first/last tick preservation logic selected them incorrectly.
- **AXIS-003:** 09:15 → next meaningful tick (e.g. ~10:10) has sensible spacing.
- **AXIS-004:** Intermediate intraday labels are present when there is sufficient horizontal space.
- **AXIS-005:** Final label around 15:15 remains visible.
- **AXIS-006:** First and last labels do not collide with chart edges.
- **AXIS-007:** Labels do not overlap candles, tooltip content or chart legend.
- **AXIS-008:** Hovering the first/last candle does not create a misleading axis/layout collision.

## 5.2 1W

- **AXIS-010:** 21 Aug and 24 Aug labels do not overlap.
- **AXIS-011:** 22 Aug / 24 Aug spacing remains readable where those dates are actual ticks.
- **AXIS-012:** Labels for 25 Aug and 29 Aug are not incorrectly dropped when enough width exists.
- **AXIS-013:** Tick selection is distributed across the week rather than clustering at one end.
- **AXIS-014:** First and last meaningful trading dates remain represented.
- **AXIS-015:** Rotated labels remain readable and are never 90° vertical.
- **AXIS-016:** Tick filtering does not alter candle aggregation or timestamps.

## 5.3 1M / 3M / 1Y

- **AXIS-020:** Labels are distributed across the full visible period.
- **AXIS-021:** Labels do not overlap after rotation.
- **AXIS-022:** Month boundaries remain understandable.
- **AXIS-023:** 1Y labels remain readable at standard desktop width.
- **AXIS-024:** First/last label edge breathing room is maintained.
- **AXIS-025:** X-axis fixes do not modify Y-axis scale or candle rendering.
- **AXIS-026:** Tick selection remains deterministic at narrow widths.

## 5.4 Responsive / Rendering

- **AXIS-030:** Test standard desktop width.
- **AXIS-031:** Test narrower desktop width.
- **AXIS-032:** Test chart resizing.
- **AXIS-033:** No clipped labels.
- **AXIS-034:** No label overlap with chart border.
- **AXIS-035:** No tooltip/legend collision caused by axis margin changes.
- **AXIS-036:** Axis collision filtering does not change timeframe aggregation semantics.

---

# 6. P0 — Candlestick vs Legacy Chart Regression

- **CANDLE-001:** Candlestick chart renders correctly on Dashboard.
- **CANDLE-002:** Candlestick chart renders correctly in Guided Research.
- **CANDLE-003:** 1D uses expected intraday aggregation.
- **CANDLE-004:** 1W uses expected weekly-period presentation.
- **CANDLE-005:** 1M, 3M and 1Y preserve expected aggregation semantics.
- **CANDLE-006:** Switching timeframe does not leak data from another timeframe.
- **CANDLE-007:** EMA overlays stay aligned with candles.
- **CANDLE-008:** Support/resistance lines stay aligned with the correct price scale.
- **CANDLE-009:** Tooltip values correspond to the hovered candle.
- **CANDLE-010:** Chart remains usable when indicators are close together.
- **CANDLE-011:** Existing line/time-series behavior not intentionally changed by candlestick work remains intact.

---

# 7. P0 — ER-0036 Persistent Trading Setup & Setup Progress

ER-0036 is currently a **domain/backend capability**, not a frontend acceptance surface.

- **SETUP-001:** TradingSetup is derived only for supported level strategies.
- **SETUP-002:** Structural entry zone is independent of today's close.
- **SETUP-003:** Moving today's price changes SetupProgress, not TradingSetup.
- **SETUP-004:** Price below zone → `awaiting_entry`.
- **SETUP-005:** Price inside zone → `in_entry_zone`.
- **SETUP-006:** Price above zone → `extended` where applicable.
- **SETUP-007:** Invalidation changes progress/action without redefining setup.
- **SETUP-008:** In-zone state never says “wait for a pullback into the zone.”
- **SETUP-009:** Trend Continuation and Pullback produce non-contradictory next-event text.
- **SETUP-010:** Non-level strategies return no structural setup.
- **SETUP-011:** Existing recommendation fields remain unchanged.
- **SETUP-012:** REST exact-key contract remains unchanged until an explicit API ER expands it.
- **SETUP-013:** Future frontend exposure must be added to this suite before release.

---

# 8. P0 — Guided Research Learning Flow

The product name is **Guided Research**. Internal route/file names may remain `LearningJourney`.

## 8.1 Navigation / Positioning

- **LEARN-001:** Sidebar says “Guided Research”.
- **LEARN-002:** Page H1 says “Guided Research”.
- **LEARN-003:** Positioning communicates study → decide → compare → learn.
- **LEARN-004:** “Learning Journey” is not accidentally displayed as the product name.
- **LEARN-005:** Existing route continues to work.

## 8.2 Study Stage

- **LEARN-010:** Stock identity and exchange are correct.
- **LEARN-011:** Price and change are correct.
- **LEARN-012:** Quick Snapshot values match chart/market data.
- **LEARN-013:** Add to Watchlist works.
- **LEARN-014:** Add to Trade Journal opens the correct workflow.
- **LEARN-015:** Journal symbol is prefilled with the researched stock.
- **LEARN-016:** Chart timeframe switching works.
- **LEARN-017:** User can study evidence before seeing Mentor view.

## 8.3 Decision Gate

- **LEARN-020:** Mentor recommendation is hidden before decision submission.
- **LEARN-021:** User must submit their own decision/thesis before Mentor reveal.
- **LEARN-022:** User decision persists.
- **LEARN-023:** Decision fields support intended action/thesis/invalidation behavior.
- **LEARN-024:** Refresh does not accidentally bypass the gate.
- **LEARN-025:** Backend reveal gate cannot be bypassed by UI-only manipulation.

## 8.4 Compare / Learn

- **LEARN-030:** Mentor view reveals only after valid decision.
- **LEARN-031:** Mentor recommendation is the same authoritative recommendation.
- **LEARN-032:** User decision and Mentor decision are displayed distinctly.
- **LEARN-033:** Correct/incorrect learning outcome is not overstated.
- **LEARN-034:** Debrief explains evidence rather than implying guaranteed profit.
- **LEARN-035:** Learning progression remains understandable to a novice trader.

---

# 9. P0 — Watchlist & Trade Journal

## Watchlist

- **TRADE-001:** Add to Watchlist creates one entry.
- **TRADE-002:** Duplicate add returns/handles 409 correctly.
- **TRADE-003:** Button changes to “In Watchlist”.
- **TRADE-004:** Existing watchlist entries are recognized on reload.
- **TRADE-005:** Correct stock symbol is persisted.
- **TRADE-006:** Recommendation displayed for watchlist stock matches single source of truth.

## Trade Journal

- **TRADE-010:** New Trade dialog retains existing default behavior.
- **TRADE-011:** Optional initial symbol pre-fills the researched stock.
- **TRADE-012:** User-entered price/quantity are not overwritten unexpectedly.
- **TRADE-013:** Trade saves successfully.
- **TRADE-014:** Saved trade appears in Journal.
- **TRADE-015:** Edit trade preserves unrelated fields.
- **TRADE-016:** Delete/cancel behavior remains correct.
- **TRADE-017:** User decision/thesis/invalidation fields persist where applicable.
- **TRADE-018:** Existing trades created before new fields remain readable.

---

# 10. P1 — API & Contract Regression

- **API-001:** Market endpoints return expected schema.
- **API-002:** Stock detail contains the expected recommendation block.
- **API-003:** Exact-key contract tests remain green unless intentionally revised by an ER.
- **API-004:** Deprecated-but-served recommendation fields remain available.
- **API-005:** `rationale == summary` where the existing contract requires it.
- **API-006:** No accidental API key renames.
- **API-007:** Error responses remain structured.
- **API-008:** Watchlist duplicate behavior remains deterministic.
- **API-009:** Trade CRUD endpoints remain backward compatible.
- **API-010:** Guided Research decision/reveal endpoints enforce the intended gate.

---

# 11. P1 — Data Persistence & Database Regression

Current application limitation: persistence is global rather than user-scoped.

- **DB-001:** Watchlist persistence survives application restart.
- **DB-002:** Trade Journal persistence survives application restart.
- **DB-003:** Settings persistence survives application restart.
- **DB-004:** Schema migration is repeatable.
- **DB-005:** Existing database opens successfully after migration.
- **DB-006:** No accidental runtime DB changes are included in source checkpoints.
- **DB-007:** No production/user data is committed into source control.
- **DB-008:** Future authentication ER must scope watchlist/trades/settings by user identity.
- **DB-009:** Guided Research history should eventually persist per user if product requirements demand cross-session learning history.

---

# 12. P1 — Security / Secrets / Environment

- **SEC-001:** No API keys or credentials committed.
- **SEC-002:** Environment-specific files are not accidentally committed.
- **SEC-003:** Localhost configuration does not leak into production configuration.
- **SEC-004:** No sensitive user data in test fixtures.
- **SEC-005:** Mentor reveal cannot be bypassed through client-side state alone.
- **SEC-006:** User decision endpoints validate input server-side.
- **SEC-007:** Future auth implementation must include session/logout behavior.
- **SEC-008:** Error messages do not expose internal secrets or database details.

---

# 13. P1 — Recommendation Provenance / Anti-Look-Ahead

This is especially important before claiming that Mentor recommendations are “accurate”.

Current engine uses dynamic indicators/levels based on current snapshot, and historical snapshots are not stored.

- **PROV-001:** Live recommendation uses only data available at recommendation time.
- **PROV-002:** Current candle may be used only where explicitly intended.
- **PROV-003:** No future candle enters current recommendation calculation.
- **PROV-004:** Support/resistance calculation uses the documented rolling window.
- **PROV-005:** RSI calculation uses the documented lookback.
- **PROV-006:** VWAP calculation uses documented lookback/session semantics.
- **PROV-007:** Recommendation is deterministic for identical input.
- **PROV-008:** Recommendation engine has no network dependency.
- **PROV-009:** Recommendation engine has no LLM dependency.
- **PROV-010:** Recommendation engine has no clock/randomness dependency.
- **PROV-011:** Before backtesting, historical indicator/level snapshots must be stored or reproducibly reconstructed without look-ahead.

---

# 14. P1 — Recommendation Validation / Accuracy Framework

Do **not** call confidence “probability of profit” until these tests exist.

## Required future dataset

For each historical decision timestamp store:

- symbol
- timestamp
- OHLCV snapshot
- EMA20/50/200
- RSI
- VWAP
- support
- resistance
- strategy
- action
- evidence/confidence score
- entry zone
- stop
- target(s)
- risk/reward
- engine version

## Accuracy tests

- **ACC-001:** Replaying a historical snapshot reproduces the original recommendation.
- **ACC-002:** No future data enters the replay.
- **ACC-003:** Forward return is measured after the recommendation timestamp.
- **ACC-004:** Stop/target outcomes are measured using explicit rules.
- **ACC-005:** Results are segmented by action.
- **ACC-006:** Results are segmented by strategy.
- **ACC-007:** Results are segmented by timeframe.
- **ACC-008:** Results are segmented by confidence/evidence-strength band.
- **ACC-009:** Win rate, average return, maximum adverse excursion and maximum favorable excursion are measured.
- **ACC-010:** Calibration is evaluated before describing evidence strength as predictive probability.
- **ACC-011:** Benchmark against a simple baseline, not only against zero.
- **ACC-012:** Avoid survivorship/look-ahead bias in the historical universe.

---

# 15. P1 — UI / UX Regression

- **UX-001:** Sidebar labels are correct.
- **UX-002:** Buttons have clear enabled/disabled states.
- **UX-003:** Success/error toasts are visible and accurate.
- **UX-004:** Empty states are meaningful.
- **UX-005:** Loading states do not flash incorrect recommendation values.
- **UX-006:** Data-quality state is visible when data is incomplete.
- **UX-007:** Recommendation wording avoids guaranteed-profit language.
- **UX-008:** Confidence/evidence-strength explanation is visible where needed.
- **UX-009:** Tooltip does not obscure critical chart information unnecessarily.
- **UX-010:** Chart legend remains readable.
- **UX-011:** CTAs do not dominate the learning experience.
- **UX-012:** Guided Research clearly distinguishes the user's call from Mentor's call.

---

# 16. P2 — Browser / Visual Regression Checklist

Run manually after chart/UI ERs.

### Dashboard
- [ ] 1D screenshot
- [ ] 1W screenshot
- [ ] 1M screenshot
- [ ] 3M screenshot
- [ ] 1Y screenshot
- [ ] Hover near first candle
- [ ] Hover near last candle
- [ ] Hover middle candle
- [ ] Verify tooltip placement
- [ ] Verify X-axis labels
- [ ] Verify EMA overlays
- [ ] Verify Support/Resistance lines
- [ ] Verify Quick Snapshot values

### Guided Research
- [ ] Study stage
- [ ] Decision form
- [ ] Mentor hidden
- [ ] Submit decision
- [ ] Mentor revealed
- [ ] Compare stage
- [ ] Learn/debrief stage
- [ ] Add to Watchlist
- [ ] Add to Trade Journal

---

# 17. P2 — Regression Cases from Issues We Already Uncovered

These should never be lost.

1. **1D X-axis starts too late** — previously first visible label appeared around 14:50 instead of 09:15.
2. **1D sparse intermediate labels** — long gap between early label and 15:15 despite available space.
3. **1W label collision** — 22/21 Aug and 24 Aug labels were too close.
4. **1W missing labels** — 25 Aug and 29 Aug disappeared unexpectedly.
5. **Rotated labels were added but collision persisted** — rotation alone is not sufficient.
6. **Tooltip can visually collide with the chart edge/axis region** — test first/last candle hover.
7. **EMA mismatch investigation** — chart hover EMA and Quick Snapshot EMA must be compared using the same timestamp/snapshot.
8. **ER-0036 has no frontend surface** — do not claim it is user-visible until an explicit frontend ER exposes setup/progress.
9. **Confidence terminology risk** — confidence is evidence strength, not probability of profit.
10. **Historical accuracy limitation** — current dynamic indicators/levels cannot be naively backtested without historical snapshots.
11. **Tracked SQLite DB creates noisy diffs** — runtime DB changes must not enter feature checkpoints.
12. **Environment file protection** — `.env.development` must not be accidentally staged.
13. **OpenCode/session interruption** — after an interrupted coding session, verify git diff/status and test state before resuming; do not assume the last command completed.
14. **Application restart behavior** — verify frontend/backend restart does not create unexpected state or database changes.
15. **Shared CandlestickChart risk** — a chart fix must be tested on every page that consumes the shared component.

---

# 18. Git / Checkpoint Regression Gate

Before every ER checkpoint:

```text
[ ] git status --short reviewed
[ ] Protected DB files excluded
[ ] Environment files excluded unless explicitly required
[ ] No secrets/credentials/API keys
[ ] git diff --check clean
[ ] Changed files mapped to ER
[ ] Tests added/updated for behavior
[ ] Existing tests pass
[ ] Production build passes
[ ] Browser smoke test completed for UI changes
[ ] No unrelated files accidentally staged
[ ] Commit message identifies ER scope
```

---

# 19. Test Result Recording Template

For every regression run record:

**Build / Commit:**  
**ER under test:**  
**Date:**  
**Environment:**  
**Browser:**  
**Backend status:**  
**Frontend status:**  

### Automated
- Backend tests: PASS / FAIL
- Frontend tests: PASS / FAIL
- TypeScript: PASS / FAIL
- Production build: PASS / FAIL
- API contract: PASS / FAIL
- `git diff --check`: PASS / FAIL

### Manual
- Dashboard: PASS / FAIL
- Chart 1D: PASS / FAIL
- Chart 1W: PASS / FAIL
- Chart 1M: PASS / FAIL
- Chart 3M: PASS / FAIL
- Chart 1Y: PASS / FAIL
- Guided Research: PASS / FAIL
- Watchlist: PASS / FAIL
- Trade Journal: PASS / FAIL

### Defects
| ID | Severity | Area | Expected | Actual | Reproducible | ER |
|---|---|---|---|---|---|---|

---

# 20. Severity Definition

**P0 — Release blocker**
- Recommendation is wrong/contradictory.
- User decision gate can be bypassed.
- Chart displays materially wrong market data.
- EMA/indicator values are materially wrong.
- Data loss or corruption.
- Build/application cannot start.

**P1 — High**
- Important workflow broken.
- Incorrect API contract.
- Significant chart/timeframe issue.
- Watchlist/Journal persistence failure.
- Security/environment regression.

**P2 — Medium**
- Readability issue.
- Non-critical UI behavior.
- Tooltip/layout issue with workaround.
- Minor copy inconsistency.

**P3 — Low**
- Cosmetic issue.
- Minor spacing/alignment issue with no functional impact.

---

# 21. Recommended Automation Roadmap

### Phase 1 — Now
Automate:
- recommendation engine
- strategy consistency
- API contract
- chart data transformation
- EMA calculations
- X-axis tick selection/collision
- Guided Research decision/reveal gate
- Watchlist duplicate behavior
- Trade Journal form logic

### Phase 2 — After ER-040
Add:
- browser E2E tests
- screenshot/visual regression for 1D/1W/1M/3M/1Y
- Dashboard ↔ Guided Research consistency checks
- tooltip/Quick Snapshot indicator consistency

### Phase 3 — Accuracy / Mentor validation
Build:
- historical recommendation snapshots
- deterministic replay
- forward-outcome measurement
- strategy/action/timeframe segmentation
- confidence/evidence-strength calibration
- benchmark comparison

**Important:** Phase 3 is the point at which TradeLens can begin making evidence-based claims about Mentor performance. Until then, “confidence” remains an internal strength-of-evidence measure, not a probability of successful trading.

---

## 22. Living Suite Rule

For every future ER:

1. Identify which existing regression cases it can break.
2. Add at least one regression test for every new business rule.
3. Add a manual browser case for every user-visible behavior.
4. Add a data/provenance test for every new analytical calculation.
5. Update the “Issues We Already Uncovered” section whenever a new defect is found.
6. Never weaken a regression assertion merely to make a new implementation pass without documenting the product decision.
7. Keep P0 tests small, deterministic and mandatory.
8. Treat Mentor/recommendation correctness as a trust-critical area.

**Baseline principle:** *Every bug we discover becomes a permanent test case unless the underlying product behavior is intentionally retired.*

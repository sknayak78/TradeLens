# TradeLens — Gemini Development Instructions

## 1. Role

You are a coding agent assisting with the TradeLens project.

Implement only explicitly assigned development tasks. Preserve existing
functionality and project history.

Do not perform unrelated refactoring, architecture changes, dependency
upgrades, branch operations, commits, pushes, merges, or rebases unless
explicitly instructed.

## 2. Git Safety — CRITICAL

Before ANY code change, run:

- `git branch --show-current`
- `git status --short`
- `git log -3 --oneline`

Report the current branch and HEAD.

Never:
- run `git reset --hard`
- run `git clean`
- run `git restore`
- run `git checkout -- <file>`
- run `git merge`
- run `git rebase`
- force-push

unless explicitly instructed.

Do not switch branches unless explicitly instructed.

Do not modify `main`.

Do not commit or push unless explicitly instructed.

Never overwrite or discard existing user changes.

If unexpected working-tree changes affect files needed for the task, STOP and
ask before modifying them.

## 3. Protected Local Files

Never intentionally modify or commit these unless explicitly required:

- `backend/tradelens.db`
- `backend/*.db`
- `backend/*.db-*`
- `frontend/.env*`
- backup files
- credentials
- API keys
- secrets

Never expose credentials.

## 4. Scope Discipline

Work only on the assigned task.

Before changing code:

1. Identify the minimum files required.
2. Inspect the existing implementation.
3. Inspect relevant tests.
4. Check relevant Git history.
5. Preserve behavior outside the requested scope.

Do not delete tests to make tests pass.

Do not silently revert previous ER functionality.

Do not opportunistically fix unrelated issues discovered during investigation.

## 5. Conflict Prevention

Before completion, run:

`grep -RInE '^(<<<<<<<|=======|>>>>>>>)' frontend/src backend 2>/dev/null`

There must be no unresolved merge-conflict markers.

## 6. Testing

For every change:

1. Run targeted tests.
2. Run relevant regression tests.
3. For frontend changes, run relevant frontend tests.
4. For frontend production-impacting changes, run `yarn build`.
5. Run `git diff --check`.

Never claim tests passed unless actually executed.

## 7. Completion Report

Report:

- What changed
- Why it changed
- Files changed
- Tests executed and exact results
- Build result where applicable
- `git diff --check` result
- Merge-conflict marker check result
- `git diff --name-status`
- Risks or limitations

Do not claim completion if validation failed.

## 8. TradeLens Product Context

TradeLens is an investment research, learning, market-analysis and trading
journal application focused initially on Indian equities/securities.

Major capabilities include:

- Market data
- Stock charts
- Technical indicators
- Learning opportunities
- Investment education
- Mentor/insight narratives
- Watchlists
- Trading Journal
- Trade thesis and lifecycle tracking

Prioritize reliability, explainability, educational value, and disciplined
investment decision support.

## 9. Architecture

Backend:
- FastAPI
- SQLAlchemy
- SQLite
- Market-data provider abstraction
- Yahoo Finance integration with seed fallback
- Recommendation/opportunity engine
- Market, watchlist, settings and trade APIs

Frontend:
- React
- TypeScript
- React Query
- React Router
- TailwindCSS
- Recharts
- Lucide

Major surfaces include:
- Dashboard
- ChartCard
- Watchlist
- Trading Journal
- Settings
- Education

## 10. Verified ER History

### ER-0029 — Launch / Education Reliability

ER-0029 included launch-readiness and education/reliability improvements,
including provider-error tolerance, opportunity evaluation/caching and
empty-universe handling.

Preserve these behaviors.

### ER-0030 — Trade Lifecycle / Mentor Snapshot

ER-0030 introduced and refined:

- Trade creation and lifecycle management
- Open and closed trade states
- Long/short handling
- Entry and exit date/price editing
- Quantity integrity
- Realized and unrealized P&L
- Duplicate trade prevention
- User journal notes
- Historical Mentor snapshot capture
- Mentor evidence/context preservation
- Close/reopen/delete behavior
- Legacy trades without Mentor snapshots

Do not regress ER-0030 journal or Mentor behavior.

Open trades must retain null exit fields and calculate unrealized P&L without
persisting a market price as an exit.

Closed trades must preserve realized P&L, quantity, exit details and immutable
Mentor snapshots.

User notes must remain separate from Mentor-generated data.

### ER-0031 — Chart Timeline / X-Axis

ER-0031 addressed chart x-axis behavior across timeframes.

The implementation provides reliable tick labels and timeframe-aware axis
behavior.

For 1Y specifically, the chart must represent actual elapsed calendar time,
not equal index spacing between trading-day data points.

### ER-0032 — 1Y Chart Correction + CTA Removal

ER-0032 finalized the 1Y chart correction.

For 1Y:

- chart points use epoch-millisecond timestamps
- XAxis uses numeric/time scaling
- domain uses actual minimum/maximum timestamps
- month-boundary tick timestamps are explicit
- labels use `MMM yyyy`

1D / 1W / 1M / 3M behavior must not be changed unnecessarily.

ER-0032 also removed the Dashboard CTA:

"Explore Today's Learning Opportunities"

The Today's Learning Opportunities panel remains.

Do not reintroduce the CTA unless explicitly requested.

## 11. Current Approved Baseline

Approved checkpoint:

`92adb7792b61631644359b0271d8faf981453907`

Commit:

`fix(er-0031): correct 1y chart time scale and remove learning CTA`

Branch:

`cursor/er-0031-chart-timeline-xaxis`

Do not change branches unless explicitly instructed.

## 12. Market Search Direction

TradeLens is intended to support discovery of Indian equities/securities
beyond the original seeded catalogue.

A Yahoo Finance discovery spike established:

- Yahoo can discover NSE equities.
- NSE filtering/ranking is required.
- `.NS` represents NSE symbols.
- ADRs, BSE securities, derivatives and other instruments must not be
  accidentally treated as NSE equities.
- Corporate rename/alias handling is required.

Do not implement this capability unless explicitly assigned.

## 13. Development Philosophy

Prefer:

- Small focused changes
- Existing project patterns
- Backward compatibility
- Explicit validation
- Minimal dependencies
- Clear error handling
- Tests alongside implementation

Avoid:

- Large rewrites
- Unrequested refactoring
- Speculative features
- Fake market data
- Fabricated prices
- Removing functionality to make tests pass

## 14. Agent Behavior

For each assigned task:

1. Restate the task briefly.
2. Inspect the relevant code and tests.
3. Check Git state.
4. Identify affected files.
5. Implement the smallest correct change.
6. Test it.
7. Review the diff.
8. Report results.

If requirements are ambiguous or a change could affect existing behavior,
STOP and ask for clarification.

If another branch or commit appears relevant, do not merge or cherry-pick it
automatically. Report it and ask.

## 15. Commits

Default: DO NOT commit.

Only create a commit when explicitly instructed.

Before an instructed commit:

- Tests must pass.
- Review `git diff --name-status`.
- Run `git diff --check`.
- Ensure database, environment, credentials and backup files are excluded.
- Create a focused commit.
- Report the commit hash.

Never push unless explicitly instructed.

## 16. Final Rule

Protect existing TradeLens work above all else.

When uncertain:

STOP.

Show the user the current state.

Ask before taking a destructive, cross-scope, or irreversible action.
# MD-11 Daily-Bar Read Path

## Status

| Phase | Scope | Commit | State |
| --- | --- | --- | --- |
| Phase 1 | Single-flight guard for `/api/opportunities` | `3c18845` fix: coalesce concurrent opportunities requests | Implemented · Committed · Pushed |
| Phase 2 | Forming daily-bar overlay | `a96240f` feat: add forming daily bar overlay | Implemented · Committed · Pushed |
| Phase 3 | `DailyBarStore` integration into the historical daily-bar read path | — | **Planned / Not started** |

All phases are on branch `er-md-01-market-data-boundary`, built on the MD-10
canonical baseline described in `MD-10-BULK-MARKET-DISCOVERY.md`. The shared
constraint across all three phases: the daily bars consumed by Stage-2 screening
must be correct, computed once, and never fetched more expensively than
necessary — without changing the MD-10 architecture or the MD-08 response
shape.

## Phase 1 — Single-flight opportunity discovery

**Problem.** With a cold cache, simultaneous `GET /api/opportunities` requests
each triggered their own full broad-market discovery scan. A dashboard that
fires several requests at once could launch duplicate scans, each competing for
the same provider budget and the same 60s discovery deadline.

**Decision.** Introduce a single-flight / in-flight guard in
`backend/routers/market.py` so one request owns the compute and the rest reuse
its result:

- one request becomes the **owner** and runs the discovery;
- **followers** wait on the in-flight compute rather than starting their own;
- followers receive the **same resulting response object** the owner built, not
  a re-serialized copy;
- the actual scan runs **outside** the synchronization lock — the lock guards
  only the flight pointer, never the compute;
- if the owner overruns the deadline, followers serve an independent request
  rather than failing, and only the owner publishes the flight outcome, so a
  wedged owner is never overwritten.

**What it is not.** This is **not** a replacement for the existing cache. It
complements `MarketDataService`'s TTL cache by preventing *concurrent*
redundant scans of a cold key; the cache continues to serve every later read
within its TTL. Cache semantics, TTLs, the response shape, and the existing
discovery and curated-fallback deadlines are all unchanged.

**Tests.** `backend/tests/test_opportunities_single_flight.py` — concurrent
cache misses share one compute, and every waiter reuses the winner's result
object.

## Phase 2 — Forming daily-bar overlay

**Problem.** During the OPEN session the daily OHLCV series consumed by Stage-2
screening ends with a *forming bar* whose close is a stale first print. RSI and
EMA therefore read a close that the market has already moved past, so screening
and the published chart disagree with the live quote.

**Decision.** `overlay_forming_bar` in `backend/services/market_scanner.py`
overlays the live quote onto today's forming daily bar before indicators are
computed. The overlay is **gated** and is skipped unless every condition holds:
provider attribution matches the Stage-1 bulk call, the last stored bar is
today in IST, and the session is such that the forming bar is the most recent
information available. A skip is logged with a reason and the original series is
returned unchanged.

**No extra provider call.** The overlay reuses the `MarketQuote` that MD-10
Stage 1 already fetched; the Stage-1 quotes are carried into Stage 2. There is
no `LiveSnapshot` type, no second provider bulk method, and no additional
provider call.

**Product note.** Daily indicators therefore move while the market is OPEN.
This is intentional: no smoothing or freezing is applied. A daily indicator
changing intraday is correct, not a defect.

**Tests.** `backend/tests/test_md_11_forming_bar_overlay.py` — overlay
application, each gating condition, session boundaries, and provider-mismatch
skip.

## Phase 3 — `DailyBarStore` integration (Planned / Not started)

**Status: planned. No commit exists and no code has been written.**

**Objective.** Make the existing `DailyBarStore` a production consumer of
historical daily-bar reads, reusing its existing per-entry TTL and
immutable-borrow cache contract. This is an **integration** task, not the
creation of a new cache — the store already exists and is fully implemented in
`backend/services/market_data/daily_store.py`.

The store is currently referenced only by its own module and by
`backend/tests/test_cache_ownership_contract.py`. It is **not yet wired into any
production read path**, which is exactly what Phase 3 changes.

**What Phase 3 must do**

- wire `DailyBarStore` into the appropriate historical OHLCV read path;
- preserve the existing `MarketDataService` provider / fallback / retry
  behaviour;
- preserve the existing immutable-borrow cache contract;
- retain the existing per-entry TTL behaviour.

**What Phase 3 must not do**

- introduce another cache, or any duplicate market-data abstraction;
- change the MD-10 bulk discovery architecture;
- change the Phase 1 single-flight implementation;
- change the Phase 2 forming-bar overlay behaviour;
- add frontend changes, discovery scheduling, or persistence of discovery
  results;
- introduce a new `LiveSnapshot` abstraction.

**Existing contracts Phase 3 must honour**

| Contract | Detail |
| --- | --- |
| Keying | Exact market-data cache key, e.g. `ohlcv:SYM:1y:1d`, so the provider series round-trips without slicing or re-derivation. |
| Per-entry TTL | Resident layer is an `InMemoryTTLCache` with per-entry TTLs; entries expire at the next NSE pre-open (09:15 IST). No background worker. |
| Session gating | Entries are only *served* outside the OPEN session, when every stored bar is final. |
| Immutable borrow | The cache makes no defensive copies. The same object is stored and returned on every hit, and one frozen `StoredSeries` is shared across reads. Consumers must treat cached values as immutable. |
| Durability | One flat JSON file per key, written atomically via a temp file and `os.replace`, so a write never rewrites unrelated entries. |
| Failure handling | Unreadable or corrupt entries log a warning and return `None`; a corrupt entry can never fail a request. |

**Store location.** `INTEL_DAILY_BARS_PATH`, defaulting to
`<tempdir>/tradelens_intel_daily_bars`.

## Regression coverage

| Area | Test file |
| --- | --- |
| Phase 1 single-flight | `backend/tests/test_opportunities_single_flight.py` |
| Phase 2 forming-bar overlay | `backend/tests/test_md_11_forming_bar_overlay.py` |
| Immutable-borrow / ownership | `backend/tests/test_cache_ownership_contract.py` |
| MD-10 baseline | `backend/tests/test_md_10_bulk_discovery.py` |

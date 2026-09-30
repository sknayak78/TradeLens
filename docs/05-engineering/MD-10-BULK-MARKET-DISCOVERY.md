# MD-10 Bulk Market Discovery

## Status

| Field | Value |
| --- | --- |
| Story | MD-10 |
| Commits | `33499de` feat: optimize broad-market opportunity discovery |
| State | Implemented · Committed · Pushed |
| Branch | `er-md-01-market-data-boundary` |
| Tests | `backend/tests/test_md_10_bulk_discovery.py` |

MD-10 is the **canonical** broad-market discovery architecture. It extends the
MD-08 pipeline; it does not replace it. See `MD-08-TODAYS-OPPORTUNITIES.md` for
the response contract and `MD-11-DAILY-BAR-READ-PATH.md` for what happens to
the daily bars this pipeline screens.

## Flow

Discovery is a two-stage funnel. Stage 1 is a single cheap bulk quote call
across the whole universe; Stage 2 spends historical reads only on a bounded
survivor set.

```text
NSE universe
  -> Stage 1  bulk quotes (one batched call)      [broad_market_prefilter.py]
  -> eligible set (year-high proximity)
  -> deterministic truncation to the Stage-2 cap
  -> Stage 2  bounded parallel historical screening [market_scanner.py]
  -> curated fallback when discovery cannot deliver an analysed shortlist
```

### Stage 1 — broad-market prefilter

`backend/services/market_data/broad_market_prefilter.py` reduces the NSE
universe to candidates near their 52-week high
(`DEFAULT_YEAR_HIGH_PROXIMITY_PCT = 10.0`). The prefilter narrows *which*
instruments are worth a historical read; it does not decide any trading view.
52-week-high proximity is the term that actually discriminates. Measured on a
live intraday sweep: within 5% -> 133, within 10% -> 452, within 25% -> 1,496
of 2,655 returned quotes.

A prefilter that is unavailable, fails, or returns nothing is **not** silently
reported as a successful prefilter. Each case records an explicit
`fallback_reason` (`bulk_prefilter_disabled`, `bulk_prefilter_unavailable`,
`bulk_prefilter_failed`, `bulk_prefilter_empty`, `bulk_prefilter_no_candidates`)
and falls through to the curated path.

### Stage-2 cap and determinism

Survivors are truncated to `DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES = 300`. The cap
is a hard limit chosen so bounded concurrency finishes inside the existing 60s
discovery deadline, and truncation is deterministic — the same universe and
inputs always select the same set. `was_capped` reports whether truncation
occurred, so a capped shortlist is never presented as a complete one.

### Bounded parallel screening

Stage 2 screens the capped set through a `ThreadPoolExecutor`. Concurrency is
bounded; the executor does not fan out one thread per instrument. A discovery
that cannot finish inside its service deadline returns `discovery_failed` with
an empty opportunity list and an explicit error rather than fabricating counts
or waiting indefinitely on a provider call.

## Canonical bulk-quote contract

`MarketQuote` (`services/market_data/models.py`) is the single normalized quote
type for a bulk batch. It is provider-neutral: no Upstox response keys, colon-form
identifiers, or HTTP shapes reach it. `instrument_key` retains the normalized
master key so a batch joins back onto the scanner's instrument universe.

Every field except `price` and `volume` is optional, because providers
legitimately omit them and malformed values must fail Stage 1 silently rather
than raise. Consumers treat `None` as *not available*, never as zero.

Bulk quotes are reached through `get_bulk_market_quotes` at every layer:

| Layer | Location |
| --- | --- |
| Provider protocol | `services/market_data_provider.py` |
| Read facade | `services/market_data_service.py` |
| Upstox implementation | `services/providers/upstox_provider.py` |

There is no second bulk-quote method and no alternative quote type.

### Deterministic batching

The Upstox implementation splits the requested keys into fixed batches of
`_MAX_QUOTE_BATCH_SIZE = 250` (`services/providers/upstox_provider.py`). Upstox's
documentation permits 500 keys, but the runtime proxy in front of
`api.upstox.com` rejects a 500-key query string with HTTP 414 (Request-URI Too
Long) while 250 succeeds with margin — verified live: 500 -> 414, and
250/200/150/100/50 -> 200. This is a **measured runtime limit, not a documented
one**, so it must not be raised to 500 without re-measuring. Batching is
deterministic, so the same request produces the same batch boundaries.

### Canonical wire format

Batches are sent as **repeated query parameters**, never a comma-joined list and
never repeated keys:

```text
?instrument_key=a&instrument_key=b
```

The single-key LTP read (`/v2/market-quote/ltp?instrument_key=<key>`) is a
separate, unrelated call and is not a bulk-batch form.

## Service-layer behaviour

Bulk quotes are read through `MarketDataService`, so they inherit the existing
documented behaviour (ADR-003):

- an ordered provider **chain** — `[Upstox, Yahoo, Seed]` when
  `MARKET_DATA_PROVIDER=upstox`; the first link gets two attempts, each later
  link one;
- the first successful provider's value is cached under the service cache key
  like every other read, so a bulk batch can never bypass the configured TTL;
- an empty result falls through to the next provider, and a `NotImplementedError`
  catalogue op is a structural skip with no retry and no health flip.

## Observability

Discovery responses and logs carry the funnel: `bulk_snapshot_requested`,
`bulk_snapshot_returned`, `stage_one_eligible_count`,
`stage_two_selected_count`, `stage_two_cap`, `bulk_prefilter_applied`, and
`bulk_prefilter_fallback_reason`. These are the numbers to read when judging
whether discovery is prefiltering effectively or falling back.

## What MD-10 is not

- It is not a replacement for the curated catalogue. The catalogue remains the
  explicit `curated_fallback`, and `sourceMode` keeps fallback distinguishable
  from broad-market discovery.
- It does not add persistence, background scheduling, or frontend-side ranking.
- It does not introduce a `LiveSnapshot` type or any other parallel market-data
  abstraction. `MarketQuote` on the path above is the only quote type.
- It does not change the MD-08 opportunities response shape; all metadata is
  additive.

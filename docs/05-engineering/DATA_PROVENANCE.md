# Data provenance and legacy fields

Where every published field comes from, and which ones are on their way out.
Written for ER-0014B, whose rule is simple: **the Recommendation Engine is the
only authority for a trading decision, and no field may contradict it.**

## Authority

| Concern | Owner |
| --- | --- |
| Trend, score, action, strategy, confidence, levels, narrative | `recommendation.engine` |
| Prices, volume, RSI, EMAs, VWAP, support/resistance, chart series | Market data provider (live) |
| Live LTP price tag | Upstox provider (`priceSource: "ltp"`) when Upstox is primary |
| Names, sectors, catalog membership, curated ranking reasons | Seed dataset |
| Instrument-key resolution (Upstox) | Versioned `NSE_EQ` instrument master (`backend/data/`) |
| Mapping to the API models | Routers, which add no logic of their own |

`services/stock_decision.decide()` is the one place that turns a provider row
into a trend and a score. Every endpoint that publishes either calls it, so a
parent field cannot drift from the `recommendation` block.

## Field provenance

### Live, recomputed on every fetch

`price`, `changePct`, `volume`, `rsi`, `ema20`, `ema50`, `ema200`, `vwap`,
`support`, `resistance`, `series`, `aiInsight`.

`vwap` is a **rolling 20-session volume-weighted average price** computed from
the same daily bars as the other indicators (`indicators/vwap.py`). Daily bars
carry no intraday detail, so this is not a single-session VWAP; it replaced a
seeded literal that survived from an era when RELIANCE traded near 2,934.

### Derived by the Recommendation Engine

`trend`, `score`, and the whole `recommendation` block.

### Intentionally seeded

These are catalog metadata or curated copy, not market data, and are safe to
serve as-is:

| Field | Why it stays seeded |
| --- | --- |
| `name`, `sector` | Instrument master data; a licensed source is not wired up. |
| Catalog membership (`GET /stocks`), `todaysFocus`, ranking `reason` | Curated product copy and a fixed universe. |
| `MARKET_INDICES` fallback values | Used only when the live index fetch fails. |
| `avg_volume`, `day_high` | Read exclusively by the deprecated analysis layer (below). A live `volume` is compared against a seeded `avg_volume`, which is one more reason not to build on that layer. |

Anything not listed above is either live or engine-derived. A failed live fetch
falls back to the **whole** seeded row, which is internally consistent — a seeded
price alongside its own seeded VWAP — rather than a mix of eras.

## MD-03: Upstox lineage

When `MARKET_DATA_PROVIDER=upstox`, the authoritative data path changes shape
but the single-source rule (ADR-001) is preserved:

- The snapshot `price` is the live Upstox LTP quote and is flagged
  `priceSource: "ltp"`; `changePct` is against the Upstox previous close.
  A daily close is never presented as a live price.
- Stock-detail responses expose `snapshotProvider`, `insightProvider`, and
  `chartProvider` so provider fallback between independent reads cannot be
  mistaken for one homogeneous source.
- `rsi`, `ema20`, `ema50`, `ema200`, `vwap`, `support`, `resistance`, the
  `aiInsight`, and the chart series all derive from the *same* Upstox OHLCV
  history — no indicator is borrowed from a different provider.
- Catalogue `name`, `sector`, `dayHigh`, `avgVolume`, `score`, `trend` stay
  seeded.  Non-catalogue instruments resolved through the bundled `NSE_EQ`
  instrument master get neutral metadata (`sector: "Equities"`,
  `trend: "neutral"`, derived day-high / average volume).
- The instrument master is a validated release artifact (≥1500 `NSE_EQ`
  records) produced by `scripts/fetch_upstox_instruments.py` and gated by
  `scripts/validate_upstox_instruments.py`; a placeholder or sample can never
  pass that gate.

## Legacy fields

All of these remain on the wire and are marked `deprecated` in the OpenAPI
schema. None of them is an input to the Recommendation Engine:
`RecommendationInput.from_snapshot()` reads only price, EMAs, RSI and
support/resistance, so a seeded `suggestedAction` or `trend` cannot influence a
recommendation.

| Field | Status | Why it still exists | Frontend dependency | Migration |
| --- | --- | --- | --- | --- |
| `suggestedAction` | Deprecated | Legacy action string from `analysis.service`; can still say "Buy on Breakout" where the engine says `Watch`. | Yes — watchlist and rankings badges. | Replace with `recommendation.action`. |
| `classification` | Deprecated | Legacy quality label ("Excellent"/"Ignore"). | Yes — rankings table. | Replace with `recommendation.conviction`. |
| `insight` | Deprecated | Indicator-centric sentence superseded by plain-English narrative. | Yes — rankings table. | Replace with `recommendation.summary`. |
| `tradeSetup` | Deprecated | Legacy setup label built from seeded VWAP/day-high inputs. | Yes — analysis badges. | Replace with `recommendation.strategy`. |
| `riskLevel` | Deprecated | Legacy risk bucket derived from the legacy score. | Yes — analysis badges. | Replace with `recommendation.levels` plus `confidence`. |
| `strengthScore` | Deprecated | Legacy 0-100 score; parallel to, and different from, `recommendation.score`. | Yes — rankings sort order. | Replace with `recommendation.score`. |
| `stars` | Deprecated | Presentation of `strengthScore`. | Yes — rankings table. | Derive from `recommendation.conviction`. |
| `aiInsight` | Live, but a candidate | Provider-generated indicator sentence ("Price 1,283.90 is below EMA20..."). | Yes — detail header. | Replace with `recommendation.summary`. |

Removal is deliberately **not** part of ER-0014B: the frontend still reads every
one of them, so they are frozen as display-only until a frontend request moves
each panel onto the `recommendation` block.

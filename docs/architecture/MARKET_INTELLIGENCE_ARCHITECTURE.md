# Market Intelligence Architecture

> Market intelligence transforms normalized market data into ranked, scored, and explained opportunities. The pipeline is deterministic, provider-neutral, and separates authoritative scoring from AI synthesis.

---

## Pipeline Overview

```
Historical Daily Store
+
Live Market Snapshot
        ↓
Normalized Market Data
        ↓
Discovery
        ↓
Ranking
        ↓
Deep Analysis
        ↓
TradeLens Score
        ↓
Prepared Intelligence
        ↓
Client API
```

Each stage is a pure function of its inputs — no hidden state, no network calls, no LLM.

---

## Stage 1: Normalized Market Data

**Inputs:** Provider adapter output (`DailyBar`, `LiveQuote`, `Instrument`)

**Output:** Unified, validated, time-aligned market data ready for analytics

### Historical Daily Store (Phase 1 — IMPLEMENTED)
- Persistent SQLite store of daily OHLCV bars
- Upsert semantics: idempotent, restart-safe
- Completed daily bars reused outside market hours
- Expiry aligned to next NSE pre-open (09:00 IST)
- Single-flight protection for concurrent fetches

### Live Market Snapshot
- **Phase 1:** Individual live quotes during market hours
- **Phase 2 (IMPLEMENTED / VALIDATED):** Provider-neutral bulk quote (Upstox v3 market-quote/quotes, 500 instruments/request) + today's forming bar overlay
- 2,656-instrument universe in 6 bulk requests with bounded concurrency, 429 retry/backoff
- Live snapshot caching with single-flight protection
- Live data never persisted to daily-bar store (only completed daily bars stored)

### Data Quality
- Gap detection in historical series
- Outlier detection (price jumps, volume spikes)
- Missing-bar interpolation policy (none — gaps remain gaps)
- Provider cross-validation where multiple providers configured

---

## Stage 2: Discovery

**Purpose:** Filter universe to relevant candidates

**Inputs:** Normalized market data + instrument master

**Output:** Ranked candidate list with discovery reasons

### Filters (IMPLEMENTED)
- Exchange: NSE equities only (`.NS` / `EQ` segment)
- Liquidity: Minimum average volume threshold
- Price range: Configurable min/max
- Active status: Not suspended, not delisted

### Ranking Factors (IMPLEMENTED)
- Relative strength vs Nifty 50
- Momentum (price change over 5/20/50 sessions)
- Volume surge vs average
- Technical structure (trend, support/resistance proximity)

### Discovery Reasons
Each candidate carries a `reason` field explaining why it surfaced:
- `momentum_breakout`
- `pullback_to_support`
- `volume_surge`
- `relative_strength`
- `oversold_bounce`

---

## Stage 3: Ranking

**Purpose:** Order candidates by opportunity quality

**Inputs:** Discovery output + deep analysis evidence (pre-computed)

**Output:** Ranked list with rank, score components, and conviction

### Ranking Algorithm (IMPLEMENTED)
- Multi-factor scoring: trend, momentum, structure, risk/reward
- Conviction bands: `high`, `medium`, `low`, `avoid`
- Deterministic tie-breaking: score → volume → alphabetical

### Output per Candidate
```python
@dataclass
class RankedCandidate:
    symbol: str
    rank: int
    score: float              # 0-100, deterministic
    conviction: str           # high/medium/low/avoid
    discovery_reason: str
    strategy: str             # Trend Continuation, Pullback, Breakout, Consolidation, No Entry Yet
    evidence: EvidenceBundle  # See Deep Analysis
```

---

## Stage 4: Deep Analysis

**Purpose:** Compute per-symbol technical evidence for scoring

**Inputs:** Normalized daily bars + live snapshot for one symbol

**Output:** `EvidenceBundle` — all deterministic analytics

### EvidenceBundle (IMPLEMENTED)
```python
@dataclass
class EvidenceBundle:
    # Trend
    trend: str                    # "bullish", "bearish", "neutral"
    ema20: Decimal
    ema50: Decimal
    ema200: Decimal
    price_vs_ema20: float         # % distance
    price_vs_ema50: float
    price_vs_ema200: float

    # Momentum
    rsi: float
    rsi_zone: str                 # "oversold", "neutral", "overbought"

    # Volatility & Volume
    atr: Decimal
    atr_pct: float                # ATR as % of price
    volume_ratio: float           # Current vs 20-session average

    # Structure
    support: Decimal
    resistance: Decimal
    distance_to_support: float
    distance_to_resistance: float

    # Risk/Reward
    risk_reward: float            # Computed from entry/stop/target
    stop_loss: Decimal
    target_1: Decimal
    target_2: Optional[Decimal]

    # Strategy Geometry
    entry_zone_low: Optional[Decimal]
    entry_zone_high: Optional[Decimal]
    invalidation_level: Decimal

    # Data Quality
    bars_count: int
    data_complete: bool
    live_overlay: bool            # True if live snapshot used
```

All values computed from normalized data — no external dependencies.

---

## Stage 5: TradeLens Score

**Purpose:** Authoritative deterministic score from evidence

**Inputs:** `EvidenceBundle` + `RankedCandidate` context

**Output:** `TradeLensScore` — single authoritative number + components

### Score Composition (IMPLEMENTED)
```
TradeLens Score = weighted combination of:
  - Trend Alignment (0-25)
  - Momentum Quality (0-20)
  - Structure Favorability (0-20)
  - Risk/Reward Ratio (0-15)
  - Volume Confirmation (0-10)
  - Data Quality (0-10)
```

### Properties
- **Deterministic:** Identical `EvidenceBundle` → identical score
- **Bounded:** 0-100, never 100 (uncertainty acknowledged)
- **Explainable:** Each component traces to evidence
- **No LLM:** Pure Python function, zero external calls

### Score → Action Mapping
| Score Range | Action | Conviction |
|-------------|--------|------------|
| 80-99 | Strong Buy | High |
| 65-79 | Buy | High/Medium |
| 50-64 | Watch | Medium |
| 35-49 | Wait | Low/Medium |
| 0-34 | Avoid | Low |

### Strategy Determination
Strategy derived from evidence geometry (not score):
- **Trend Continuation:** Price in trend, pullback to EMA20/50, favorable R/R
- **Pullback:** Price in trend, deeper pullback to support/EMA50, zone defined
- **Breakout:** Price at resistance, volume surge, awaiting close above
- **Consolidation:** Range-bound, no clear edge
- **No Entry Yet:** Trend broken, avoidance warranted

---

## Stage 6: Prepared Intelligence

**Purpose:** Pre-compute intelligence for efficient API responses

**Current State (Phase 1 — IMPLEMENTED):**
- On-demand computation via `/api/opportunities` with single-flight protection
- Full-universe scan on each request (cached daily bars)
- Response includes: ranked candidates, evidence, score, strategy, AI synthesis

**Phase 2 (IMPLEMENTED / VALIDATED):**
- Live-edge optimization: Upstox bulk quote + forming bar overlay
- Same on-demand model; faster live data integration (~0.78s live snapshot acquisition measured, not a guaranteed SLA)
- 32 deterministic Phase 2 tests; live validation: 2,655 usable instruments, 1 missing (TAALTECH)

**Long-Term Direction (PLANNED):**
- **Prepared Intelligence APIs:** Background computation writes prepared results to store
- Client APIs read prepared intelligence (sub-second response)
- Eliminates synchronous full-universe scan on user request
- Event-driven refresh: market close, significant price move, schedule

---

## Phase Status Summary

| Phase | Component | Status |
|-------|-----------|--------|
| **Phase 1** | Persistent daily-bar store | **IMPLEMENTED** |
| | Completed daily data reuse | **IMPLEMENTED** |
| | NSE pre-open expiry alignment | **IMPLEMENTED** |
| | Single-flight opportunity computation | **IMPLEMENTED** |
| | Technical indicators (EMA, RSI, VWAP, S/R, ATR) | **IMPLEMENTED** |
| | Discovery, Ranking, Deep Analysis | **IMPLEMENTED** |
| | TradeLens Score (deterministic) | **IMPLEMENTED** |
| | Recommendation Engine v1.1 | **IMPLEMENTED** |
| | Strategy-driven recommendations | **IMPLEMENTED** |
| | AI synthesis layer (separate) | **IMPLEMENTED** |
| **Phase 2** | Provider-neutral live snapshot abstraction | **IMPLEMENTED / VALIDATED** |
| | Upstox bulk v3 market-quote/quotes (500/request) | **IMPLEMENTED / VALIDATED** |
| | 2,656 universe in 6 requests, bounded concurrency | **IMPLEMENTED / VALIDATED** |
| | 429 retry/backoff, missing-instrument tolerance | **IMPLEMENTED / VALIDATED** |
| | Forming-bar overlay (OPEN market) | **IMPLEMENTED / VALIDATED** |
| | Live snapshot caching + single-flight | **IMPLEMENTED / VALIDATED** |
| | Yahoo standalone mode preserved | **IMPLEMENTED / VALIDATED** |
| | 32 deterministic Phase 2 tests | **IMPLEMENTED / VALIDATED** |
| | Live validation: 2,655 usable / 1 missing | **IMPLEMENTED / VALIDATED** |
| **Future** | Incremental historical refresh | **PLANNED** |
| | Continuous/background intelligence | **PLANNED** |
| | Prepared intelligence APIs | **PLANNED** |
| | HDFC / Zerodha / Groww / Angel One / ICICI adapters | **PLANNED** |

---

## API Contract

### GET /api/opportunities
Returns ranked opportunities with full evidence.

```json
{
  "universe": "nse_equities",
  "as_of": "2026-01-15T15:30:00Z",
  "opportunities": [
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries",
      "rank": 1,
      "score": 78,
      "conviction": "high",
      "action": "Buy",
      "strategy": "Trend Continuation",
      "discovery_reason": "momentum_breakout",
      "evidence": { ... },
      "levels": {
        "entry_zone": [2450, 2480],
        "stop_loss": 2380,
        "targets": [2600, 2720]
      },
      "ai_synthesis": "RELIANCE shows strong trend continuation..."
    }
  ],
  "meta": {
    "computation_ms": 1250,
    "cache_hit": true,
    "live_overlay": true
  }
}
```

### GET /api/stocks/{symbol}
Returns deep analysis for a single symbol (same evidence as opportunities).

---

## Data Flow Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| Single source of truth | ADR-001: All analytics from same OHLCV dataset |
| Strategy consistency | ADR-002: Strategy is parent; levels/narrative derived |
| Deterministic scoring | ADR-004: Pure function, no LLM, no network, no clock |
| AI boundary | ADR-005: AI receives score+evidence, produces narrative only |
| Cache correctness | ADR-006: Daily bars persisted, expiry at NSE pre-open, single-flight |

---

## Future Evolution

### Incremental Historical Refresh (PLANNED)
- Detect gaps in daily-bar store
- Fetch only missing ranges per provider
- Reconcile overlapping provider data
- Configurable lookback windows

### Continuous Intelligence (PLANNED)
- Background worker computes opportunities periodically
- Prepared intelligence table updated asynchronously
- Client APIs read prepared results (fast)
- Refresh triggers: schedule (pre-market, post-market), price alerts, volume spikes

### Prepared Intelligence API (PLANNED)
```json
GET /api/intelligence/prepared
{
  "as_of": "2026-01-15T15:30:00Z",
  "opportunities": [...],  // Pre-computed
  "stale": false
}
```

---

## References

- ADR-001: Single Source of Truth for Market Data
- ADR-002: Strategy is the Parent Trading Thesis
- ADR-003: Provider/Broker Adapter Strategy
- ADR-004: Deterministic Market Intelligence Pipeline
- ADR-005: AI Synthesis Boundary
- ADR-006: Market Intelligence Cache and Prepared Data
- `docs/architecture/PROVIDER_ADAPTER_ARCHITECTURE.md`
- `docs/architecture/TRADELENS_SCORE_INTELLIGENCE_MODEL.md`
- `docs/05-engineering/DATA_PROVENANCE.md`
- `docs/05-engineering/ENGINEERING_REQUESTS.md` (ER-0014, ER-0016, ER-0036)
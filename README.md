# TradeLens

TradeLens is an **open-source, self-hosted market-intelligence and investment-research platform** for Indian markets.

TradeLens is the **intelligence layer**, not the broker. Users run TradeLens on their own infrastructure and bring their own broker/data-provider entitlements and credentials.

---

## What TradeLens Is

- A self-hosted platform for market research and intelligence
- Provider-neutral: bring your own data source (Upstox, Yahoo, future: HDFC, Zerodha, Groww, Angel One, ICICI)
- Read-only intelligence: market data, technical analysis, discovery, ranking, scoring, AI-assisted explanation
- Deterministic scoring engine (TradeLens Score) with AI synthesis layer
- No order execution in initial scope

---

## Architecture Overview

```
Provider/Broker Adapter
        ↓
Normalized Market Data
        ↓
Market Intelligence
        ↓
Deterministic Analytics
        ↓
TradeLens Score
        ↓
AI Synthesis / Explanation
        ↓
Client APIs
        ↓
Web / Future React Native + Expo
```

- **Provider/Broker Adapter**: Isolates provider-specific APIs and authentication
- **Normalized Market Data**: Unified OHLCV, instrument master, quote format
- **Market Intelligence**: Discovery, ranking, deep analysis
- **Deterministic Analytics**: Technical indicators, evidence computation
- **TradeLens Score**: Authoritative deterministic score — no LLM involved
- **AI Synthesis**: Explains evidence and score; never overrides authoritative score
- **Client APIs**: Backend remains client-independent (web today, mobile planned)

---

## Provider / Broker Adapters

| Provider | Status | Scope |
|----------|--------|-------|
| Upstox | **IMPLEMENTED** | Read-only market data |
| Yahoo Finance | **IMPLEMENTED** | Standalone/fallback mode |
| HDFC Securities / InvestRight | **PLANNED** (Next) | Read-only market data |
| Zerodha / Kite | **PLANNED** | Read-only market data |
| Groww | **PLANNED** | Read-only market data |
| Angel One / SmartAPI | **PLANNED** | Read-only market data |
| ICICI Direct / Breeze | **PLANNED** | Read-only market data |

> Initial integrations are READ-ONLY. Order execution is NOT in scope.

---

## Yahoo Standalone Mode

TradeLens runs fully with Yahoo Finance as the sole data source — no broker credentials required. This is the default development mode and a valid production deployment option.

---

## Credential & Security Model

- Provider credentials are **user-owned secrets**
- Credentials **remain on the backend/runtime** — never sent to frontend/mobile
- Credentials **never committed to Git**
- Credentials **never logged** or included in diagnostics
- Credentials **never returned** through API responses
- Each provider's auth is isolated behind its adapter

---

## TradeLens Score & AI Boundary

- **TradeLens Score is deterministic** — computed from market evidence only
- **AI does not calculate the authoritative score**
- **AI synthesizes and explains** the deterministic evidence and score
- **No LLM dependency** in the authoritative scoring path
- Confidence/evidence strength reflects supporting evidence, not probability of profit

---

## Market Intelligence (Current State)

### IMPLEMENTED (Phase 1)
- Persistent daily-bar store (OHLCV)
- Restart-safe persistence
- Completed daily data reuse outside market hours
- Cache expiry aligned to next NSE pre-open
- Single-flight protection for concurrent opportunity computation
- Technical indicators: EMA 20/50/200, RSI, VWAP (rolling 20-session), Support/Resistance
- Recommendation Engine v1.1 (single source of truth)
- Strategy-driven recommendations with consistent entry/stop/target logic

### IMPLEMENTED / VALIDATED (Phase 2)
- Provider-neutral live market snapshot abstraction
- Upstox bulk v3 market-quote/quotes (500 instruments/request, 6 requests for 2,656 universe)
- Bounded concurrency, 429 retry/backoff, missing-instrument tolerance
- Forming-bar overlay during OPEN market; historical bars unchanged
- Live snapshot caching with single-flight protection
- Yahoo standalone mode remains supported
- 32 deterministic Phase 2 tests; live validation: 2,655 usable / 1 missing (TAALTECH)

### PLANNED (Future)
- Incremental historical data refresh
- Continuous/background intelligence refresh
- Prepared intelligence APIs (avoid synchronous full-universe scans)

---

## Configuration

Development configuration lives in `.env.development`:

```dotenv
BACKEND_PORT=8001
FRONTEND_PORT=3000
REACT_APP_BACKEND_URL=http://localhost:8001
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_CACHE_TTL_SECONDS=30
```

| Variable | Description |
|----------|-------------|
| `MARKET_DATA_PROVIDER` | `yahoo` or `upstox` |
| `MARKET_DATA_CACHE_TTL_SECONDS` | Cache TTL for market data |
| `UPSTOX_API_KEY` | Upstox API key (when using Upstox) |
| `UPSTOX_API_SECRET` | Upstox API secret (when using Upstox) |

> **Never commit `.env*` files.** Credentials must remain local.

---

## Development Setup

### Prerequisites
- macOS/Linux with Bash, Python 3.11+, Node.js 18+, npm
- Backend dependencies in `backend/venv`
- Frontend dependencies in `frontend/` via `npm install`

### Commands (from repository root)

| Command | Description |
|---------|-------------|
| `make dev` | Starts FastAPI + React dev server using `.env.development` |
| `make backend` | Starts only the FastAPI backend |
| `make frontend` | Starts only the React frontend |
| `make test` | Runs backend tests |
| `make lint` | Runs whitespace, shell, Python, and JS config checks |

Equivalent scripts in `scripts/`:
```bash
./scripts/dev.sh
./scripts/backend.sh
./scripts/frontend.sh
./scripts/test.sh backend
./scripts/test.sh frontend
./scripts/test.sh all
./scripts/lint.sh
```

---

## Deployment

TradeLens is designed for self-hosting. See `docs/deployment/` (to be created) for production deployment guidance covering:
- Container/Podman/Docker deployment
- Reverse proxy (nginx/Caddy)
- SSL/TLS termination
- Environment variable management
- Database backup/restore
- Process supervision

---

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/05-engineering/ENGINEERING_ROADMAP.md` | Product & engineering roadmap with IMPLEMENTED/ACCEPTED/PLANNED status |
| `docs/05-engineering/ARCHITECTURE_DECISIONS.md` | Architecture Decision Records (ADRs) |
| `docs/architecture/PROVIDER_ADAPTER_ARCHITECTURE.md` | Provider adapter pattern, credential isolation, integration guide |
| `docs/architecture/MARKET_INTELLIGENCE_ARCHITECTURE.md` | Market intelligence pipeline, Phase 1/2 status, future direction |
| `docs/architecture/TRADELENS_SCORE_INTELLIGENCE_MODEL.md` | Deterministic scoring model, evidence, AI boundary |
| `docs/01-product/PRODUCT_VISION.md` | Product vision and mission |
| `docs/01-product/PRODUCT_PRINCIPLES.md` | Guiding product principles |
| `docs/02-product-design/MENTOR_ENGINE_SPEC.md` | Mentor engine specification (stages 1-2 implemented) |
| `docs/05-engineering/DATA_PROVENANCE.md` | Field provenance and deprecation map |
| `docs/05-engineering/ENGINEERING_REQUESTS.md` | Engineering request log with statuses |

---

## License

MIT License — see `LICENSE` file.
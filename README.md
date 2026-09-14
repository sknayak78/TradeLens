# TradeLens

TradeLens is an AI-assisted day-trading dashboard for Indian markets. The
repository contains a FastAPI/SQLite backend and a React/TypeScript frontend.

## Prerequisites

- macOS with Bash, Python 3, Node.js, and npm available on `PATH`
- Backend dependencies installed in `backend/venv` (or the repository-root
  `venv`)
- Frontend dependencies installed with `npm install` in `frontend/`

## Developer toolkit

Run all commands from the repository root.

Development configuration lives in [`.env.development`](.env.development).
Every development script loads this file automatically. Edit it to configure
ports, the frontend backend URL, and market-data provider/cache settings.

```dotenv
BACKEND_PORT=8001
FRONTEND_PORT=3000
REACT_APP_BACKEND_URL=http://localhost:8001
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_CACHE_TTL_SECONDS=30
```

`MARKET_DATA_PROVIDER` selects the market-data primary: `yahoo` (default),
`seed` (offline demo), or `upstox`.  Upstox mode reads a valid versioned
`NSE_EQ` instrument master and a live quote token:

```dotenv
MARKET_DATA_PROVIDER=upstox
UPSTOX_ACCESS_TOKEN=<token, never committed>
UPSTOX_INSTRUMENT_MASTER=backend/data/upstox_instruments.json
```

With Upstox primary, the snapshot price is the live Upstox LTP
(`priceSource: "ltp"`) and every indicator/chart derives from the same Upstox
OHLCV dataset (ADR-003).  The bundled master is produced at release time with
`scripts/fetch_upstox_instruments.py` and verified with
`scripts/validate_upstox_instruments.py`; `scripts/validate_upstox_live.py`
probes the live Upstox path with a real token.
The checked-in artifact is deployment-gated and must continue to pass the
1500-record validation threshold before activation.

| Command | Description |
| --- | --- |
| `make dev` | Starts FastAPI and the React development server using `.env.development`. |
| `make backend` | Starts only the FastAPI backend. |
| `make frontend` | Starts only the React frontend. |
| `make test` | Runs backend tests. |
| `make lint` | Runs whitespace, shell syntax, Python syntax, and JavaScript configuration checks. |

The equivalent scripts are available in `scripts/`:

```bash
./scripts/dev.sh
./scripts/backend.sh
./scripts/frontend.sh
./scripts/test.sh backend
./scripts/test.sh frontend
./scripts/test.sh all
./scripts/lint.sh
```

Update `.env.development` to change local configuration; scripts and Make
targets use the new values on their next run.

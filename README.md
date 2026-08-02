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

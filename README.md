# TradeLens

TradeLens is an AI-assisted day-trading dashboard for Indian markets. The
repository contains a FastAPI/SQLite backend and a React/TypeScript frontend.

## Prerequisites

- macOS with Bash, **Python 3.12**, Node.js, and npm available on `PATH`
- Backend dependencies installed in `backend/venv` (or the repository-root
  `venv`)
- Frontend dependencies installed with `npm install` in `frontend/`

## Python runtime

Supported backend interpreter: **`>=3.12,<3.14`**. Python **3.12** is the
validated development runtime and the version the repository defaults to
(`.python-version`).

**Python 3.14 is not supported.** `backend/requirements.txt` pins
`SQLAlchemy==2.0.36`, and that release is incompatible with Python 3.14. It
calls `typing.Union.__getitem__` unbound; under Python 3.14 `typing.Union`
became a class whose `__getitem__` is a descriptor, so the call fails while
mapping `backend/models.py`:

```text
TypeError: descriptor '__getitem__' requires a 'typing.Union' object
           but received a 'tuple'
```

Create the backend virtual environment with Python 3.12 explicitly. Do **not**
use a bare `python3 -m venv`, because a default `python3` on current macOS
installs is 3.13+ and will reproduce the failure above:

```bash
python3.12 -m venv backend/venv
source backend/venv/bin/activate
```

If a specific interpreter lives outside `PATH`, use its full path, for example
on Homebrew/macOS:

```bash
/usr/local/bin/python3.12 -m venv backend/venv   # Intel Homebrew prefix
/opt/homebrew/bin/python3.12 -m venv backend/venv # Apple Silicon Homebrew prefix
```

Then install the pinned dependencies:

```bash
./backend/venv/bin/pip install -r backend/requirements.txt
```

`./scripts/backend.sh` and `./scripts/test.sh backend` verify the interpreter
version before running and fail fast with an explanatory message when it is
outside the supported range, instead of surfacing the SQLAlchemy traceback.

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

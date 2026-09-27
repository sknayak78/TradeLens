# TradeLens Frontend

React + TypeScript frontend for the TradeLens market-intelligence platform.

---

## Quick Start

```bash
cd frontend
npm install
npm start
```

Runs on `http://localhost:3000` (configured via `REACT_APP_BACKEND_URL` in `.env.development` at repo root).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + TypeScript |
| Build | Create React App (react-scripts) |
| State/Data | React Query (TanStack Query) |
| Routing | React Router v6 |
| Styling | TailwindCSS |
| Charts | Recharts |
| Icons | Lucide React |
| HTTP | Fetch API (via React Query) |

---

## Project Structure

```
frontend/
├── public/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── chart/        # ChartCard, CandlestickChart, indicators
│   │   ├── common/       # Button, Card, Badge, Loading, ErrorBoundary
│   │   ├── layout/       # Sidebar, Header, PageContainer
│   │   └── recommendation/ # RecommendationCard, LevelsDisplay, AIInsight
│   ├── hooks/            # Custom React hooks (useStock, useWatchlist, etc.)
│   ├── pages/            # Route-level page components
│   │   ├── Dashboard.tsx
│   │   ├── StockDetail.tsx
│   │   ├── GuidedResearch.tsx
│   │   ├── Watchlist.tsx
│   │   ├── TradeJournal.tsx
│   │   └── Settings.tsx
│   ├── services/         # API client, query keys, types
│   │   ├── api.ts        # Fetch wrappers, endpoint definitions
│   │   ├── queries.ts    # React Query hooks and keys
│   │   └── types.ts      # TypeScript interfaces for API responses
│   ├── utils/            # Formatters, helpers, constants
│   ├── App.tsx           # Routes, providers
│   ├── main.tsx          # Entry point
│   └── index.css         # Tailwind imports + global styles
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── .env.development      # Not committed; copied from root .env.development
```

---

## Key Architectural Patterns

### API Layer (`src/services/`)
- Centralized `api.ts` with typed fetch wrappers
- React Query hooks in `queries.ts` for caching, deduping, retries
- TypeScript interfaces mirror backend OpenAPI schema
- No business logic in components — all data fetching via hooks

### Chart Components (`src/components/chart/`)
- `CandlestickChart` — shared across Dashboard, StockDetail, GuidedResearch
- Timeframe switching: 1D, 1W, 1M, 3M, 1Y
- EMA overlays (20/50/200), Support/Resistance lines, Volume pane
- X-axis: epoch-millisecond timestamps; 1Y uses actual calendar time
- Tooltip: OHLCV + EMA values at hover point

### Recommendation Display (`src/components/recommendation/`)
- `RecommendationCard` — renders authoritative `recommendation` block
- `LevelsDisplay` — entry zone, stop, targets (only for level strategies)
- `AIInsight` — separate AI synthesis panel (loads async, non-blocking)
- Legacy fields (`suggestedAction`, `strengthScore`, etc.) still consumed where `recommendation` not yet adopted

### State Management
- **Server state:** React Query (cache, background refetch, deduping)
- **Client state:** React `useState`/`useContext` (UI toggles, form inputs)
- **No global state library** — kept simple intentionally

### Routing
```
/
├── /                    → Dashboard
├── /stock/:symbol       → StockDetail
├── /research/:symbol    → Guided Research (Study → Decide → Compare → Learn)
├── /watchlist           → Watchlist
├── /journal             → Trade Journal
└── /settings            → Settings
```

---

## Development

### Environment Variables

Create `frontend/.env.development` (not committed):

```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

The root `.env.development` is the source of truth; `scripts/dev.sh` copies relevant vars.

### Commands

| Command | Description |
|---------|-------------|
| `npm start` | Dev server with hot reload |
| `npm test` | Jest + React Testing Library (watch mode) |
| `npm run build` | Production build to `build/` |
| `npm run lint` | ESLint + Prettier check |

### Adding a New Page

1. Create `src/pages/NewPage.tsx`
2. Add route in `App.tsx`
3. Add sidebar link in `src/components/layout/Sidebar.tsx`
4. Add API hooks in `src/services/queries.ts` if needed

---

## Testing

- Unit tests: `src/**/*.test.tsx` (Jest + RTL)
- Run: `npm test` or `./scripts/test.sh frontend`
- Target: Critical paths (recommendation display, chart interactions, journal forms)

---

## Production Build

```bash
npm run build
```

Outputs to `frontend/build/` — served by backend in production or deployed separately.

---

## Documentation References

- Backend API: `docs/architecture/` (provider adapters, intelligence pipeline, scoring)
- Regression suite: `docs/docs/06-testing/TradeLens_Regression_Suite.md`
- Engineering roadmap: `docs/05-engineering/ENGINEERING_ROADMAP.md`
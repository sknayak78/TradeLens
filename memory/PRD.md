# TradeLens — PRD

## Original Problem Statement
Build TradeLens: a clean, lightweight React + TypeScript + Tailwind dashboard with a TradingView-style dark theme. **Phase 1** (frontend, Feb 12 2026): Header, Sidebar, and 4-card Dashboard (Today's Focus, Top Opportunities, Watchlist, Chart & AI Insight) driven by mock JSON. **Phase 2** (backend, Feb 12 2026): a lightweight FastAPI + SQLAlchemy + SQLite backend exposing REST endpoints for watchlist, trades, settings, market summary, opportunities, and stock detail. Frontend rewired via a service layer + React Query with retry-once, loading/empty/error states, and a Settings React Context.

## Architecture
- **Frontend**: React 19 + TypeScript + Tailwind + Recharts + React Router 7 + TanStack Query 5 (retry:1)
  - `services/*` — axios-based service layer (no direct API calls in components)
  - `hooks/*` — React Query hooks (`useWatchlist`, `useTrades`, `useSettings`, `useMarket`)
  - `context/SettingsContext.tsx` — settings via Context
  - `components/common/*` — `LoadingState`, `EmptyState`, `ErrorState`
- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite
  - `server.py` — app factory + router registration + startup seeding
  - `database.py` · `models.py` · `schemas.py`
  - `routers/watchlist.py · trades.py · settings.py · market.py`
  - `seed_data.py` — static NSE catalogue, indices, opportunities, insights

## Database Schema (SQLite — `/app/backend/tradelens.db`)
- **watchlist**(id, symbol UNIQUE, created_at)
- **trades**(id, trade_date, symbol, entry_price, exit_price, quantity, notes)
- **settings**(id, capital, risk_per_trade, preferred_timeframe) — single row keyed id=1

## REST API
- `GET /api/health`
- `GET/POST/DELETE /api/watchlist` · `DELETE /api/watchlist/{symbol}` (returns enriched rows joining static market data)
- `GET/POST /api/trades` · `DELETE /api/trades/{id}` (derives `pnl` + `side` on read; SHORT pnl = (entry−exit)*qty)
- `GET/PUT /api/settings`
- `GET /api/market-summary` (indices, todaysFocus, status, asOf)
- `GET /api/opportunities`
- `GET /api/stock/{symbol}` (curated for RELIANCE/TATAMOTORS/ADANIENT/ASIANPAINT, synthesized for others)
- `GET /api/stocks?q=` (search for header dropdown)

## Implemented Features
### v0.1 (Feb 12, 2026) — Frontend MVP
- Dashboard, Watchlist, Journal, Settings pages
- Header (logo · live stock search · refresh · settings)
- Sidebar with mobile drawer, market ticker
- Recharts line chart with S/R reference lines and AI insight text

### v1.0 (Feb 12, 2026) — Backend integration
- FastAPI + SQLAlchemy + SQLite backend, seeded default watchlist
- Service + hook layer replaces all mock JSON imports
- Add/remove watchlist symbols from header search and `/watchlist`
- Trading Journal — add trade dialog (persisted to SQLite), delete trades
- Settings — capital, risk-per-trade, timeframe persisted server-side
- Loading spinners, empty states, error states with retry buttons on every data panel
- React Query retry:1 for queries & mutations
- Refresh button invalidates all React Query caches

## Prioritized Backlog
### P1
- Position sizing calculator using capital × risk in the New Trade dialog
- Journal filters (date range, symbol) + CSV export
- Optimistic UI for watchlist add/remove

### P2
- Sector heatmap widget
- Candlestick chart mode with volume histogram
- Alert builder (client-side rules over market data)
- Persist chart's selected symbol per user

### P3 (needs external data)
- Live NSE/BSE data via broker/API
- Auth + per-user watchlists and journals
- AI insights via LLM with real market context

## Known Constraints
- Market/opportunities/stock endpoints serve static seed values (intentional for MVP)
- No auth — a single global settings row & shared watchlist/trades
- Recharts logs a benign `width(-1)/height(-1)` warning on first mount

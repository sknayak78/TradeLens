# TradeLens — PRD

## Original Problem Statement
Build TradeLens: a clean, lightweight, **frontend-only** React + TypeScript + Tailwind CSS web app with a modern dark theme inspired by TradingView. No auth, no databases, no APIs, no backend logic. All data is mocked via local JSON. Must include a Header (logo, search, refresh, settings), Left Sidebar (Dashboard, Watchlist, Trading Journal, Settings), and a Dashboard with 4 cards:
1. Today's Focus — Best Setup, Momentum Stock, Watch for Breakout, Avoid Today
2. Top Opportunities — table (Stock, Score, Trend, Price) with 10 sample stocks
3. Watchlist — Stock, Price, RSI, EMA20, VWAP, Score, Trend
4. TradingView-style Chart placeholder + Trend, Support, Resistance, AI Insight

Must be responsive with reusable components.

## User Choices
- TypeScript (`.tsx`) — react-scripts + craco + typescript@4.9.5
- Classic TradingView dark theme (deep navy #131722, surface #1e222d, green/red accents)
- Simple animated line chart using **recharts**
- Mock JSON stored under `/src/mocks/`, loaded via `/src/services/marketService.ts`
- Mock files: `stocks.json`, `watchlist.json`, `opportunities.json`, `insights.json`, `marketSnapshot.json`, `todaysFocus.json`, `settings.json`

## Architecture
- **Frontend**: React 19 + TypeScript + Tailwind + Recharts + React Router 7
- **State**: Local component state (no store)
- **Data**: JSON mocks → `marketService.ts` (Promise-based) → components
- **Backend**: Not used (dormant FastAPI template stays)

## Implemented Features (Feb 12, 2026 — v0.1)
- Global TradingView-inspired dark shell (`AppShell`, `Header`, `Sidebar`, `MarketTicker`)
- Header: TradeLens logo, live stock search dropdown, spinning Refresh button + timestamp, Settings shortcut
- Left sidebar navigation with active route highlight + mobile drawer
- Market snapshot ticker (Nifty 50, Bank Nifty, India VIX)
- Dashboard 4-card bento grid:
  - Today's Focus (4 curated tiles)
  - Top Opportunities (10-row score-bar table)
  - Watchlist (10-row table w/ RSI colouring, click updates chart)
  - Chart & AI Insight (recharts line, S/R reference lines, timeframe chips, symbol chips, AI text)
- Watchlist page (dedicated route)
- Trading Journal page (stats + 4 sample trades)
- Settings page (theme, timeframe, refresh interval, notifications, compact mode toggles)
- Fully responsive: cards stack on mobile, sidebar collapses to drawer
- All interactive elements carry `data-testid` attributes

## Prioritized Backlog
### P1 (near-term polish)
- Persist Settings + Watchlist to localStorage
- Trading Journal: add/edit trade modal with local persistence
- Global keyboard shortcuts (`/` search, `g d` dashboard, etc.)

### P2 (nice to have)
- Sector heatmap widget
- Candlestick chart mode (lightweight-charts) with volume histogram
- Alert builder (client-side rule engine over mock data)
- CSV export of watchlist and journal

### P3 (future — needs backend)
- Live NSE/BSE data via broker/API
- Auth + user-owned watchlists and journals
- AI insights via LLM with real market context

## Users
- **Day trader**: fast scanning of setups, momentum, and levels
- **Swing trader**: watchlist + journal to review setups over days
- **Learner**: dashboard reveals what a professional cockpit looks like

## Known Constraints
- All data is MOCKED — refresh only jitters a timestamp; prices are static
- No persistence — settings resets on reload
- Chart is intraday-only regardless of timeframe chip selection (visual only)

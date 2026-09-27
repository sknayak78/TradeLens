# TradeLens Frontend Architecture

> Documents the actual current frontend architecture. No invented patterns.

---

## Overview

React 18 + TypeScript single-page application built with Create React App. Communicates with FastAPI backend via REST APIs. Designed for future React Native / Expo mobile client sharing the same API contract.

---

## Component Architecture

### Component Categories

| Category | Path | Purpose |
|----------|------|---------|
| **Pages** | `src/pages/` | Route-level components; compose features |
| **Features** | `src/components/<feature>/` | Feature-specific components (chart, recommendation, journal) |
| **Common** | `src/components/common/` | Generic reusable UI primitives |
| **Layout** | `src/components/layout/` | App shell: Sidebar, Header, PageContainer |

### Component Guidelines

- **Pages** import from **Features** and **Common**, not vice versa
- **Features** import from **Common** only
- **Common** has no internal dependencies
- **Layout** wraps pages; pages don't import Layout

### Shared Chart Component

`CandlestickChart` (`src/components/chart/CandlestickChart.tsx`) is the single chart implementation used by:
- Dashboard (quick view)
- StockDetail (full chart)
- GuidedResearch (study stage)

Props interface:
```typescript
interface CandlestickChartProps {
  data: ChartDataPoint[];           // OHLCV + indicators
  timeframe: Timeframe;             // 1D | 1W | 1M | 3M | 1Y
  indicators: IndicatorConfig;      // Which EMAs, S/R to show
  onHover?: (point: ChartPoint) => void;
  height?: number;
}
```

---

## Data Fetching & State

### React Query (TanStack Query) — Primary Server State

**Configuration** (`src/services/queries.ts`):
- `staleTime: 30_000` (30s) — matches backend cache TTL
- `cacheTime: 5 * 60_000` (5 min)
- `refetchOnWindowFocus: false`
- `retry: 1` (fail fast for debugging)

**Query Keys** (structured, invalidatable):
```typescript
// Single stock detail
['stock', symbol, timeframe]

// Opportunities (ranked universe)
['opportunities', universe, filters]

// Watchlist
['watchlist']

// Trade journal
['journal', filters]

// Settings
['settings']
```

**Hooks Pattern**:
```typescript
// src/services/queries.ts
export const useStock = (symbol: string, timeframe: Timeframe) =>
  useQuery({
    queryKey: ['stock', symbol, timeframe],
    queryFn: () => api.getStock(symbol, timeframe),
    enabled: !!symbol,
  });
```

Components use hooks — no direct `fetch`/`axios` in components.

### Client State — React Built-ins

- `useState` for form inputs, UI toggles, modal visibility
- `useContext` for authenticated user (future), theme (future)
- No Redux, Zustand, Jotai — not needed at current scale

---

## API Client

### `src/services/api.ts`

Centralized fetch wrapper with:
- Base URL from `REACT_APP_BACKEND_URL`
- JSON request/response
- Error normalization (HTTP error → typed `ApiError`)
- Request/response TypeScript interfaces

```typescript
// Example
export const getStock = async (symbol: string, timeframe: Timeframe): Promise<StockDetailResponse> => {
  const res await fetch(`${BASE_URL}/api/stocks/${symbol}?timeframe=${timeframe}`);
  if (!res.ok) throw await normalizeError(res);
  return res.json();
};
```

### TypeScript Types

`src/services/types.ts` mirrors backend OpenAPI schema:
- `StockDetailResponse` — includes `recommendation` block + legacy fields
- `OpportunityResponse` — ranked list with evidence
- `Recommendation` — authoritative block (action, strategy, levels, AI synthesis)
- `Trade`, `WatchlistItem`, `Settings` — CRUD types

---

## Major Surfaces

### Dashboard (`/`)
- Market indices strip (Nifty, Bank Nifty, VIX)
- Today's Opportunities: top 5 ranked cards
- Quick chart for selected symbol
- Watchlist summary

### Stock Detail (`/stock/:symbol`)
- Full `CandlestickChart` with timeframe selector
- Recommendation card (authoritative block)
- Key metrics: price, change, volume, indicators
- AI synthesis panel (async load)
- Add to Watchlist / Journal actions

### Guided Research (`/research/:symbol`)
Four-stage flow (preserved from ER-0029/ER-0030):
1. **Study** — Chart + evidence, Mentor hidden
2. **Decide** — User submits thesis/action/invalidation
3. **Compare** — Mentor reveal (same authoritative recommendation)
4. **Learn** — Debrief, comparison, journal entry prompt

### Watchlist (`/watchlist`)
- List of saved symbols with live recommendation badges
- Remove action
- Navigate to Stock Detail

### Trade Journal (`/journal`)
- CRUD for trades (symbol, entry/exit, qty, P&L, thesis, notes)
- Mentor snapshot preserved at close (ER-0030)
- Filter by open/closed, date range

### Settings (`/settings`)
- Data provider selection (Yahoo / Upstox)
- Cache TTL
- Display preferences (theme future)

---

## Styling

- **TailwindCSS** — utility-first, configured in `tailwind.config.js`
- **Design tokens**: Colors, spacing, typography in `tailwind.config.js`
- **Dark mode**: Not implemented (future)
- **Responsive**: Mobile-first breakpoints; Sidebar collapses on < 768px

---

## Chart Implementation Details

### Timeframe Aggregation
- **1D**: Intraday (5-min bars from provider or synthetic from daily)
- **1W**: Daily bars, last 5 sessions
- **1M**: Daily bars, ~21 sessions
- **3M**: Daily bars, ~63 sessions
- **1Y**: Daily bars, ~252 sessions; X-axis uses actual timestamps (not index)

### Indicators Rendered
- EMA 20 (blue), EMA 50 (orange), EMA 200 (green)
- Support (green dashed), Resistance (red dashed)
- Volume bars (color-coded by up/down day)
- VWAP (purple) — rolling 20-session

### X-Axis (ER-0031/ER-0032)
- 1D: Intraday labels (09:15, 10:15, ..., 15:15)
- 1W/1M/3M: Date labels (Mon, Tue... or MMM DD)
- 1Y: Month boundaries (MMM YYYY) with actual timestamp scaling
- Label collision avoidance: rotation + filtering

---

## Error Handling

- **API Errors**: `ApiError` with `code`, `message`, `details`; surfaced via toast
- **Network Errors**: Retry via React Query; offline banner (future)
- **Validation Errors**: Form-level inline messages
- **Error Boundaries**: `ErrorBoundary` wrapper per page (prevents full app crash)

---

## Testing Strategy

| Layer | Tool | Scope |
|-------|------|-------|
| Unit | Jest + RTL | Hooks, utils, pure components |
| Integration | Jest + RTL | Page components with mocked queries |
| E2E | Not yet | Planned: Playwright for critical flows |
| Visual | Manual | Chart rendering across timeframes |

Run: `npm test` or `./scripts/test.sh frontend`

---

## Build & Deploy

### Development
```bash
npm start  # Port 3000, proxies API to BACKEND_PORT
```

### Production Build
```bash
npm run build  # Outputs to build/
```
- Minified, hashed filenames
- Static assets served by backend (FastAPI `StaticFiles`) or CDN

### Environment
- `.env.development` for local (not committed)
- Production env injected at deploy time (no `.env` in image)

---

## Future: React Native / Expo

Backend APIs are client-independent. Mobile app will:
- Share `src/services/types.ts` (API contracts)
- Share `src/services/api.ts` logic (fetch wrapper)
- Implement native chart (react-native-svg-charts or similar)
- Use same React Query patterns for caching

---

## Known Technical Debt

1. **Legacy field consumption** — Some components still read `suggestedAction`, `strengthScore`, `aiInsight` (provider-generated) instead of `recommendation` block. Migration tracked in `DATA_PROVENANCE.md`.
2. **No global error boundary reporting** — Errors logged to console only.
3. **Chart prop drilling** — `CandlestickChart` receives many props; could use compound component pattern.
4. **Type duplication** — Some types duplicated between `types.ts` and component props; could centralize.
5. **No Storybook** — Component documentation/manual testing ad-hoc.

---

## References

- Backend API: `docs/architecture/`
- Regression suite: `docs/docs/06-testing/TradeLens_Regression_Suite.md`
- Engineering roadmap: `docs/05-engineering/ENGINEERING_ROADMAP.md`
- Data provenance: `docs/05-engineering/DATA_PROVENANCE.md`
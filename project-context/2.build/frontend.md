# B2 Frontend - Minimal Operational Console

Status: Draft for Agentic Architect review  
Persona: @frontend.eng  
Date: 2026-06-14  
Source artifacts: `project-context/1.define/prd.md`, `project-context/1.define/sad.md`, `project-context/2.build/build-plan.md`, `project-context/2.build/setup.md`, `project-context/2.build/backend.md`

## 1. Scope Completed

B2 implemented the first operator-facing Angular + PrimeNG console on top of B1 backend read contracts.

Implemented:

- Typed Angular API client for B1 read models:
  - `GET /api/health`;
  - `GET /api/configuration/summary`;
  - `GET /api/strategies`;
  - `GET /api/models`;
  - `GET /api/operation/status`;
  - `GET /api/events?limit=50`.
- PrimeNG operational shell with tabs for:
  - operation;
  - models and strategies;
  - training placeholders;
  - operational events.
- Professional dashboard frame with side navigation, contextual top bar, safety/readiness command plane, and dense operational panels.
- Status summary for backend state, selected strategy, approved/active models, open positions, and pending commands.
- TradingView Lightweight Charts wrapper with local placeholder candlesticks, paper entry/exit markers, and equity curve.
- Empty/unavailable states for strategy registry, model registry, training pipeline evidence, and event log.
- Deferred loading for chart and table-heavy registry/event views to keep the initial Angular bundle below the production error budget. The chart uses idle-triggered deferral so it appears in mobile full-page rendering without requiring the operator to switch views.

## 2. Documentation Consulted

Context7 was consulted before frontend implementation:

- Angular `/websites/angular_dev`: standalone bootstrap, router outlet/link patterns, `provideHttpClient`, and `HttpClient` dependency injection setup.
- TradingView Lightweight Charts `/tradingview/lightweight-charts`: v5 `createChart`, `addSeries(CandlestickSeries)`, `addSeries(LineSeries)`, resize handling, and v5 `createSeriesMarkers` marker management.

PrimeNG MCP was consulted before PrimeNG component implementation:

- `Tabs`: current `TabsModule`, `p-tabs`, `p-tablist`, `p-tab`, `p-tabpanels`, and `p-tabpanel` usage.
- `Table`: current `TableModule` for tabular registry/event views.
- `Tag`: current `TagModule` for status/severity labels.
- `Card`: current `CardModule` for bounded operational panels.
- `Button`: current `ButtonModule` for refresh control.

## 3. Frontend Structure

New files:

- `frontend/src/app/api/operator-api.ts`
  - Owns typed B1 read-model contracts and API calls.
- `frontend/src/app/charts/trade-chart.component.ts`
  - Owns Lightweight Charts lifecycle and local placeholder chart data.
- `frontend/src/app/models-view.component.ts`
  - Owns model and strategy registry tables.
- `frontend/src/app/events-view.component.ts`
  - Owns operational event table.

Updated files:

- `frontend/src/app/app.ts`
  - Uses the API service and PrimeNG console modules.
- `frontend/src/app/app.html`
  - Defines the B2 operator console frame, navigation, command plane, and views.
- `frontend/src/app/app.scss`
  - Defines responsive professional dashboard layout, rail navigation, table/card/chart constraints, and operational spacing.

## 4. API and Safety Boundaries

The B2 frontend only consumes backend `/api/*` read contracts already created in B1.

B2 did not add:

- direct database access;
- direct log-file access;
- direct model artifact access;
- exchange access;
- credential handling;
- trade execution controls;
- live/paper start or stop controls.

The chart uses local placeholder data because candle, equity, position, order, fill, and marker read models are later increments. The UI labels this data as placeholder so it is not confused with exchange or backtest evidence.

## 5. Intentional Non-Scope

B2 did not implement:

- historical data collection status APIs;
- real candle/equity read APIs;
- model training or approval commands;
- strategy selection commands;
- paper or live operation controls;
- authentication;
- streaming or polling loops beyond manual refresh.

## 6. Review Evidence

Executed successfully:

```bash
npm --prefix frontend run build
```

Result:

- Angular production build completed successfully.
- Remaining warnings: initial bundle exceeds the 500 kB warning budget but remains below the 1 MB error budget; root component style exceeds the 4 kB warning budget but remains below the 8 kB error budget.
- Chart, model registry, and event views are emitted as lazy chunks.

```bash
cd backend
uv run pytest
```

Result:

- `4 passed`.
- Existing FastAPI/Starlette TestClient deprecation warning remains unchanged.

Runtime smoke checks executed successfully with a temporary SQLite database:

- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:4200/api/operation/status`
- `HEAD http://127.0.0.1:4200/`

Playwright visual verification executed after installing Chromium browser dependencies in the container:

- Desktop screenshot: `/tmp/smart-trade-b2-desktop.png`
- Desktop full-page screenshot: `/tmp/smart-trade-b2-desktop-full.png`
- Mobile screenshot: `/tmp/smart-trade-b2-mobile.png`
- Mobile full-page screenshot after UX adjustment: `/tmp/smart-trade-b2-mobile-full-v2.png`

Visual findings addressed:

- Mobile full-page capture initially showed the chart placeholder because viewport-triggered deferral did not fire during full-page screenshot capture; changed chart deferral to idle.
- Mobile topbar actions initially stacked vertically; adjusted the mobile layout to keep the status tag and refresh control in line.

## 7. Next Agent Handoffs

Recommended next step after Agentic Architect approval: B3.

`@backend.eng`:

- Implement historical data ingestion and feature pipeline read models.
- Add backend data availability endpoints needed by the B2 training placeholders.

`@frontend.eng`:

- Replace B2 placeholder data with backend-provided candle/equity/marker read models when B3/B6 APIs exist.

`@qa.eng`:

- Validate B2 build, backend contract compatibility, frontend empty states, and absence of unsafe command/exchange/credential paths.

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

---

# B3 Frontend Update - Data Pipeline Visibility

Status: Draft for Agentic Architect review  
Persona: @frontend.eng  
Date: 2026-06-14

## 1. Scope Completed

B3 updated the operational console to consume backend data pipeline status.

Implemented:

- Added typed Angular contract for `GET /api/data/status`.
- Included market data status in the dashboard read-model load.
- Replaced B2 Training placeholders for historical data and feature schema with real status values:
  - persisted candle count;
  - generated feature row count;
  - latest candle timestamp;
  - latest feature schema ID;
  - latest ingestion run status and row counts.

## 2. Documentation Consulted

Context7 was consulted for Angular standalone component, `HttpClient`, signals, and template control-flow guidance.

PrimeNG MCP was consulted for:

- `Card`;
- `Tag`;
- `ProgressBar` applicability. B3 did not add `ProgressBar`; the UI stayed with compact data panels and tags.

## 3. Verification

Executed successfully:

```bash
npm --prefix frontend run build
```

Result:

- Angular production build completed successfully.
- Remaining warnings: initial bundle exceeds the 500 kB warning budget but remains below the 1 MB error budget; root component style exceeds the 4 kB warning budget but remains below the 8 kB error budget.

Runtime smoke checks:

- `GET http://127.0.0.1:4200/api/data/status`
- `HEAD http://127.0.0.1:4200/`

Playwright screenshot:

- `/tmp/smart-trade-b3-operation.png`

## 4. Intentional Non-Scope

B3 did not replace the operation chart's local placeholder data. Real operational chart markers/equity remain tied to later B6 paper-operation read models.

---

# B4 Frontend Update - Strategy Requirements Visibility

Status: Draft for Agentic Architect review  
Persona: @frontend.eng  
Date: 2026-06-14

## 1. Scope Completed

B4 updated the operational console to expose backend strategy plugin requirements.

Implemented:

- Extended the typed Angular strategy contract with:
  - `parameter_schema`;
  - `compatibility`;
  - strategy risk rules under compatibility.
- Updated the Strategy Registry table to show:
  - required model role labels;
  - required feature count;
  - compatibility tag (`READY` or `BLOCKED`).

## 2. Documentation Consulted

Context7 was consulted for Angular standalone component imports, template helpers, and built-in pipe/component template patterns.

PrimeNG MCP was consulted for:

- `Table`;
- `Tag`.

## 3. Verification

Executed successfully:

```bash
npm --prefix frontend run build
```

Result:

- Angular production build completed successfully.
- Remaining warnings: initial bundle exceeds the 500 kB warning budget and root component style exceeds the 4 kB warning budget; both remain below error budgets.

## 4. Intentional Non-Scope

B4 frontend did not implement strategy selection controls or parameter editing. Selection remains available through backend API/command contract for this increment.

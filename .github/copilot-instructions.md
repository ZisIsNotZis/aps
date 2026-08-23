# Copilot instructions for this repository

## Build, test, and lint commands

### Frontend (`frontend/`)

- Install deps: `npm ci`
- Dev server: `npm run dev` (Vite on `:5173`, proxies `/api` to backend `:8000`)
- Build: `npm run build`
- Preview build: `npm run preview`
- E2E tests (Playwright): `npx playwright test --config=playwright.config.js`
- Single E2E test file: `npx playwright test tests/universal-aps.spec.js --config=playwright.config.js`
- Single E2E test by name: `npx playwright test tests/universal-aps.spec.js -g "opens the item-function model surface and can validate and plan a sample setup" --config=playwright.config.js`

### Backend (`backend/`)

- Run API: `uv run python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- Test suite (stdlib unittest): `uv run python -m unittest discover -s tests -p "test_*.py"`
- Single test module: `uv run python -m unittest tests.test_scenarios`
- Single test case: `uv run python -m unittest tests.test_scenarios.ScenarioApiTests.test_scenario_lifecycle_create_run_approve_release`

### Lint

- No dedicated lint command is currently checked in (`frontend/package.json` has no lint script; backend has no lint config file in repo).

## High-level architecture

- This is a split app: a Vue 3 + Vite frontend (`frontend/`) and a FastAPI backend (`backend/`).
- `frontend/src/App.vue` is the main UI surface and contains APS Studio, Universal Config flows, scenario operations, integration actions, and the item-function lab; API calls are made to `/api/*` and routed by Vite proxy.
- `backend/main.py` is a compatibility entrypoint that re-exports from `aps.api`; tests and uvicorn use `main:app`.
- `backend/aps/api.py` is the core planner service:
  - Defines `PlanningInput` / `PlanningResult` schemas.
  - Builds operations from products/orders/workflows.
  - Solves scheduling with OR-Tools CP-SAT.
  - Exposes `/api/plan`, `/api/plan/check`, `/api/plan/diagnose`, scenario lifecycle endpoints, and integration sync/export/callback endpoints.
- `backend/aps/persistence.py` owns SQLite persistence (`backend/data/aps.db`) for scenarios, scenario runs, idempotency cache, and universal config tables.
- `backend/aps/universal/api.py` extends the same FastAPI app with `/api/universal/*` and `/api/item-function/*` endpoints; it compiles universal records into `PlanningInput` (currently planning compilation is gated to `discrete_manufacturing_advanced` template).
- `backend/aps/universal/item_function/` is an independent planning kernel (`schema -> normalization -> validation -> compiler -> planner`) currently solved by `GreedySolver`.

## Key conventions in this codebase

- Time unit convention is mixed by layer:
  - Input models use `*_hour` fields.
  - Solver internals convert to minute ticks (`tick_minutes = 1`).
  - `ScheduledBlock.start/end/duration` are minute-based values relative to `planning_start_iso`.
- The backend API is intentionally import-compatible from both `main` and `aps.api`; keep public symbols stable when moving code.
- Scenario and universal config mutations use optimistic concurrency:
  - Scenarios require `expected_version`.
  - Universal configs require `expected_revision`.
  - Published universal configs are immutable; clone before modifying.
- Integration endpoints are idempotent by contract (`idempotency_key`) and persist/reuse prior responses.
- Universal planning endpoints are template-gated; do not assume every universal template can compile to `PlanningInput`.
- Item-function planning APIs run explicit validation first and return 400 from the first validation error.
- Backend tests use `unittest` (not pytest). Many integration tests spawn uvicorn on fixed local ports and hit real HTTP endpoints; others call the ASGI app directly via a local `_request` helper.

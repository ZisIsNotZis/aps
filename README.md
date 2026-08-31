<p align="center">
  <img src="aps-logo.svg" width="112" alt="APS logo">
</p>

<h1 align="center">APS · Advanced Planning & Scheduling</h1>

<p align="center"><strong>Turn item flows, resources, rules, and orders into an executable production plan.</strong><br>
APS is an experimental, local-first planning workbench: model a manufacturing system in a typed JSON/Pydantic schema, compile it into constraints, solve it with interchangeable algorithms, and inspect the schedule in a browser.</p>

<p align="center"><a href="README.zh-CN.md">简体中文</a> · English</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg" alt="AGPL-3.0-only"></a>
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/Python-%E2%89%A53.12-3776AB?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="frontend/package.json"><img src="https://img.shields.io/badge/Vue%203%20%2B%20Vite-42b883?logo=vuedotjs&logoColor=white" alt="Vue 3 and Vite"></a>
  <a href="backend/tests"><img src="https://img.shields.io/badge/tests-Pytest%20%2B%20Playwright-45ba63" alt="Pytest and Playwright"></a>
</p>

> 🚧 **Status: active experiment.** APS is a research/product prototype, not a validated MES/ERP replacement. APIs and solver behavior may change.

## Why APS?

Production planning is often split between spreadsheets, opaque vendor systems, and one-off scheduling scripts. APS explores a transparent middle layer where the model, compiler, solver, and resulting Gantt schedule are inspectable in one place.

Its useful differentiators today are **one unified item-flow model**, **multiple solver strategies**, **nine built-in manufacturing scenarios**, and a local web UI that makes the plan visible instead of returning an unexplained number. The included benchmark reports **9/9 correctness** for the greedy, CP-SAT, and fluid solvers on its scenario suite; treat those numbers as project-specific experiments, not general guarantees.

## ✨ What is included

- **APS Studio** — browser UI for exploring the planning model and business resources.
- **Unified Planner** — load scenarios, edit entities/rules/orders, run a plan, and inspect order outcomes, blocks, and an SVG Gantt chart.
- **Typed planning schema** — entities, selectors, transformation rules, orders, holding rules, deadlines, release times, and money-based objectives.
- **Compiler and evaluator** — validates the model, compiles restricted expressions, simulates inventory/resource effects, and scores results.
- **Solver plugins** — greedy list scheduling, OR-Tools CP-SAT, fluid proportional-fairness simulation, plus optional Gurobi and Java Timefold integrations.
- **Scenario library** — discrete manufacturing, electronics, job shop, assembly line, food, automotive, furniture, pharma, and semiconductor examples.

### Solver snapshot

The repository’s recorded benchmark gives a useful orientation: **greedy ~1s**, **fluid ~14s**, **CP-SAT ~20s** on its benchmark setup. Greedy is fastest; CP-SAT is generally strongest on money objectives; fluid is a distinct feasibility-oriented approach. Hardware, dependencies, and model size change these results.

## 🚀 Quick start

Prerequisites: Python **3.12+**, Node.js/npm, and either `uv` or a Python environment. The default backend dependencies include FastAPI, Pydantic, OR-Tools, Gurobi Python bindings, and PyTorch; optional solver integrations have additional requirements.

```bash
git clone https://github.com/zisisnotzis/aps.git
cd aps

# Install frontend dependencies once
cd frontend && npm ci && cd ..

# Start backend + frontend with hot reload
./run.sh
```

Open <http://localhost:5173>. The backend listens on <http://localhost:8000>; health is available at `/api/health`. Start only one side with `./run.sh -b` or `./run.sh -f`.

Backend-only setup and tests:

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
```

## 🧭 Usage

1. Open **Unified Planner** and choose a built-in scenario.
2. Load it to inspect entities, rules, and orders.
3. Edit the model in the browser where useful, then select **Run Plan**.
4. Read status, makespan, block count, order outcomes, scheduled blocks, and the Gantt chart.

The HTTP surface is intentionally small:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/unified/scenarios
curl http://localhost:8000/api/unified/scenarios/discrete_manufacturing
```

The planning endpoint accepts a `PlanningModel` JSON document at `POST /api/unified/plan`; validation is available at `POST /api/unified/validate`. See [`backend/aps/unified/_schema.py`](backend/aps/unified/_schema.py) and [`docs/unified-aps-model.md`](docs/unified-aps-model.md) for the model contract.

## 🔬 Advanced paths

- Compare algorithm behavior with `backend/benchmark_solvers.py`, `backend/benchmark_scale.py`, and the recorded [`docs/benchmark-results.md`](docs/benchmark-results.md).
- Add a scenario generator and register its metadata in `backend/aps/unified/scenarios/registry.py`.
- Add a solver plugin under `backend/aps/unified/solvers/`; the plugin registry keeps dispatch separate from the schema and API.
- Study the restricted expression DSL in [`backend/aps/unified/_expr.py`](backend/aps/unified/_expr.py). It allows model formulas without evaluating arbitrary Python.

## 🎯 Goals and non-goals

**Goals:** a readable planning kernel; reproducible scenario generation; swappable solvers; inspectable constraints and results; a practical UI for learning and iteration.

**Non-goals:** replacing a production ERP/MES; promising globally optimal plans for every model; providing a multi-tenant hosted service; accepting arbitrary executable expressions; hiding solver trade-offs behind a single “best” answer.

## Roadmap

- Stabilize the model/schema and error messages.
- Make solver selection and limits explicit in the UI/API.
- Expand correctness and performance benchmarks with reproducible hardware/configuration.
- Improve persistence, import/export, and scenario authoring.
- Harden authentication, deployment, and operational observability before any network-facing use.

Ultimately, APS could become a transparent planning laboratory or an embeddable scheduling service for teams that want to inspect and tailor the optimization layer. That future depends on stronger validation, explainability, and production hardening.

## ⚠️ Caveats

- The default development server is for local use; CORS is configured for local frontend origins only.
- Gurobi requires a valid installation/license. Timefold requires Java 21+ and its built JAR; both are optional.
- Solver output can be heuristic, time-limited, or experiment-specific. Always validate schedules against real capacity, calendars, quality, safety, and business constraints before acting on them.
- The repository currently contains archived design notes and intentionally unfinished experiments; read the maturity labels and tests before building on a surface.

## Contributing

Issues and focused pull requests are welcome. Please include a small reproducible model for solver changes, update tests when behavior changes, and report objective/makespan/block-count effects. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Agents can help triage issues, investigate failures, add tests, update docs, and
implement accepted changes; maintainers review and merge contributions.

## Versioning

The backend package is currently `0.1.0`. Release notes live in Git history;
tag public releases from a reviewed commit after tests and documentation agree.
See [`docs/project-status.md`](docs/project-status.md) for scope and evidence.

## License

APS is available under the [GNU Affero General Public License v3.0-only](LICENSE).

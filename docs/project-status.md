# APS project status

## Classification

**Useful, experimental software.** APS is runnable, inspectable planning
software with a browser workbench, backend API, typed model, and solver suite.
It is not a validated production MES/ERP replacement.

## Evidence

- The backend exposes health, scenario, validation, and planning endpoints.
- The frontend presents the unified planner and an SVG Gantt view.
- The repository contains backend unit tests and frontend Playwright tests.
- The recorded July 2026 solver report covers nine scenarios and four solvers.

## Current version and limits

The Python package is version `0.1.0`; the frontend is an internal `0.0.0`
application. There is no public release artifact yet. Solver results are
experiment-specific and must be checked against real manufacturing constraints.

## Media and research

No reviewed screenshot, recording, introduction-video package, or formal paper
is present in this checkout. Prepare those manually after the UI and benchmark
claims stabilize; do not infer production evidence from archived design notes.

# APS project status

## Classification

**Useful software (closed milestone).** APS is runnable, inspectable planning software with a browser workbench, backend API, typed model, and solver suite. It was never a validated production MES/ERP replacement.

## Status

Closed as a milestone (2026-09-29). The workbench reached its stated goal; no
active development is planned unless the project's inputs or goals change.

## Evidence

- The backend exposes health, scenario, validation, and planning endpoints.
- The frontend presents the unified planner and an SVG Gantt view.
- The repository contains backend unit tests and frontend Playwright tests.
- The recorded July 2026 solver report covers nine scenarios and four solvers.

## Current version and limits

The Python package is version `0.1.0`; the frontend is an internal `0.0.0` application. There is no public release artifact yet. Solver results are experiment-specific and must be checked against real manufacturing constraints.

## Deferred

A stable public release artifact, reviewed screenshots/recordings, and a formal
paper package were left undone.

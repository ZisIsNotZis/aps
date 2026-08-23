# Contributing to APS

Thanks for helping make APS better. This is an experimental planning system,
so small, focused changes are especially welcome.

## Before opening a change

1. Explain the scheduling behavior or user-facing problem being addressed.
2. Keep changes scoped; do not commit virtual environments, `node_modules`,
   build output, logs, or local secrets.
3. Add or update a focused backend test or Playwright coverage when behavior
   changes.
4. Run the checks below and include notable limitations in the pull request.

```bash
cd backend
uv run pytest
uv run ruff check .

cd ../frontend
npm ci
npm run build
```

For larger model or solver changes, include a small reproducible scenario and
describe any effect on solver time, makespan, block count, or objective value.

## Pull requests

Use a short, descriptive title. State what changed, how it was verified, and
what remains experimental. Please do not include proprietary production data.

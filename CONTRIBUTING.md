# Contributing to Python Work Order Service

Thank you for contributing. This repository is currently a **FastAPI starter** with health endpoints and platform scaffolding. Keep changes aligned with that scope unless you are intentionally adding a new domain feature.

## Prerequisites

- Python 3.13+
- PostgreSQL and Redis available locally (or via Docker on your machine/network)
- Git

## Development setup

```bash
git clone <your-repo-url>
cd python-work-order-service

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
cp .sample_env .env        # edit POSTGRES_URI, REDIS_* , etc.
```

Run the API:

```bash
PYTHONPATH=src python -m app.main
```

Verify:

- API docs: `http://localhost:8080/docs`
- Health: `http://localhost:8080/api/v1/health`

## Code quality tools

- **Ruff** — lint/format
- **Black** — formatting
- **isort** — import sorting
- **MyPy** — static typing
- **Pylint** — additional analysis
- **pre-commit** — git hooks

Install hooks:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

Run manually:

```bash
pre-commit run --all-files
ruff check src
mypy src
black src && isort src
```

## Testing

The configured test entry point is the health suite:

```bash
pytest
pytest tests/v1/test_health.py -v
pytest --cov=src --cov-report=term-missing
```

Other files under `tests/` are legacy from the previous work-order-service codebase and are **not** collected by default. Re-enable them only after restoring the corresponding application modules.

## Coding standards

- PEP 8, line length 100
- Type hints on public functions
- Async-only database access (no sync SQLAlchemy sessions)
- Pydantic models for request/response validation
- Standardized errors via `response_factory` / exception handlers

### FastAPI conventions

- Versioned routes under `src/app/api/v1/`
- Register new routers in `src/app/api/v1/__init__.py`
- Use dependency injection for DB sessions and shared concerns

### Database conventions

- SQLAlchemy 2.x async patterns
- Schema changes via Alembic migrations (add versions under `src/migrations/versions/` before documenting `alembic upgrade head`)

## Development workflow

1. Create a branch: `git checkout -b feature/short-description`
1. Implement changes with tests
1. Run lint + tests locally
1. Open a PR with a clear summary and test plan

### Commit message format

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code restructuring
- `test:` tests only
- `chore:` maintenance

## Pull request checklist

- [ ] Code follows project conventions
- [ ] Tests added/updated for changed behavior
- [ ] Docs updated when setup, endpoints, or architecture change
- [ ] No secrets committed (`.env` stays local)
- [ ] Lint and health tests pass

## Reference vs active code

When adding files, mark reference-only examples clearly in PR descriptions. Active code must import cleanly and be registered in routers or startup lifecycle.

## Getting help

- Read [README.md](README.md) and [PROJECT_FLOW.md](PROJECT_FLOW.md)
- Open a GitHub issue for bugs or feature proposals

Thank you for helping build this service.

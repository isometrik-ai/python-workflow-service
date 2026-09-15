# Python Work Order Service

FastAPI service for maintenance work orders: assets, contracts, scheduling, vendor portal, invoices, payments, and outbound webhooks.

## Active API surface

All routes are under `/api/v1` unless noted. Auth: **API key** (`x-api-key` + tenant/project headers), **internal token** (`x-internal-token`), or **vendor token** (`x-vendor-token`). **MCP** is at `/api/mcp` (same API key auth).

| Area             | Routes                                                               |
| ---------------- | -------------------------------------------------------------------- |
| Health           | `GET /health`, `GET /metrics`                                        |
| API keys         | `GET/POST/DELETE /api-keys`                                          |
| Asset categories | CRUD `/asset-categories`                                             |
| Custom fields    | CRUD `/custom-fields`                                                |
| Assets           | CRUD `/assets` (`custom_field_values` dict)                          |
| Form templates   | `GET/POST/PATCH/DELETE /form-templates`                              |
| Contracts        | CRUD `/contracts`                                                    |
| Work orders      | CRUD + timeline `/work-orders`                                       |
| Invoices         | CRUD + timeline `/invoices`                                          |
| Payments         | CRUD `/payments`                                                     |
| Triggers         | CRUD + test `/triggers`                                              |
| Logs             | `GET /audit-events`, `GET /webhook-deliveries`, `GET /api-call-logs` |
| Business profile | `GET/PUT /business-profile`                                          |
| PDF templates    | CRUD `/pdf-templates`                                                |
| Vendors          | `GET /vendors`, `GET /vendors/search`, `POST /vendors`               |
| Scheduler        | `POST /scheduler/run`                                                |
| Vendor portal    | `GET/PATCH /vendor/work-order`, invoices                             |
| Uploads          | `GET /upload/presigned-url`                                          |
| MCP (JSON-RPC)   | `POST/GET /api/mcp`                                                  |

Contract create/update/delete triggers **immediate scheduler recompute** (work-order generation/cancellation). Background workers start automatically when `ENVIRONMENT` is not `test`:

| Worker    | Embedded (default local)           | Separate container (Docker Compose)                                   |
| --------- | ---------------------------------- | --------------------------------------------------------------------- |
| Scheduler | `WOM_EMBEDDED_SCHEDULER=true`      | `scheduler-worker` → `python -m app.workers.cli.run_scheduler_worker` |
| Webhooks  | `WOM_EMBEDDED_WEBHOOK_WORKER=true` | `webhook-worker` → `python -m app.workers.cli.run_webhook_worker`     |

Compose sets `WOM_EMBEDDED_*=false` on the API service and runs dedicated worker containers (same pattern as `python-social-service`).

See **[docs/CHANGES_FROM_REFERENCE_BACKEND.md](docs/CHANGES_FROM_REFERENCE_BACKEND.md)** for a team summary of changes vs the reference `order-management/backend` app. For the full parity matrix, see **[docs/PARITY_WITH_REFERENCE_BACKEND.md](docs/PARITY_WITH_REFERENCE_BACKEND.md)**.

## Project layout

```
src/app/
├── api/v1/              # thin routers
├── business/services/   # domain orchestration
├── crud/                # crud_* singletons
├── models/              # SQLAlchemy ORM
├── schemas/             # Pydantic + enums
├── workers/             # webhook worker, scheduler loop
└── core/                # config, security, db, utils
```

## Prerequisites

- Python 3.13+
- PostgreSQL
- Redis (required for non-test startup)

## Configuration

Copy `.sample_env` to `.env` and set at minimum:

```env
ENVIRONMENT=local
POSTGRES_URI=postgresql+asyncpg://postgres:password@localhost:5432/work_order_service
POSTGRES_SCHEMA=fm
REDIS_URL=redis://localhost:6379/0
WOM_INTERNAL_SERVICE_TOKEN=change-me-internal-token
WOM_SCHEDULER_ENABLED=true
WOM_SCHEDULER_INTERVAL_MINUTES=60
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .sample_env .env
cd src && alembic upgrade head
PYTHONPATH=src python -m app.main
```

Or:

```bash
PYTHONPATH=src uvicorn app.main:app --reload --port 8080
```

### Docker Compose

```bash
cp .sample_env .env
docker compose up --build
```

Health check:

```bash
curl "http://localhost:8080/api/v1/health?include_db=true&include_cache=true"
```

## Database schema

- **Runtime:** `connect_to_postgres()` creates the configured PostgreSQL schema (default **`fm`**, via `POSTGRES_SCHEMA`) and missing tables via SQLAlchemy `create_all`.
- **Migrations:** Alembic `20260912_000001` creates the initial `work_order` schema; `20260913_000006` renames it to **`fm`**. ORM models use text IDs (`contract_*`, `work_order_*`, etc.).
- If you previously applied a UUID-based migration, drop and recreate: `DROP SCHEMA IF EXISTS fm CASCADE; DROP SCHEMA IF EXISTS work_order CASCADE;` then `alembic upgrade head`.

## Tests

```bash
PYTHONPATH=src pytest -q
```

Configured paths: all `tests/v1/test_*.py` for routed modules plus `tests/unit/`.

## Docstrings

Ruff enforces full **pydocstyle (`D`)** rules on all `src/app/**` code (Google convention). Tests and migrations are exempt. Pre-commit will fail on missing or malformed docstrings in application code.

## Related docs

- [PROJECT_FLOW.md](PROJECT_FLOW.md) — architecture and layering
- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow

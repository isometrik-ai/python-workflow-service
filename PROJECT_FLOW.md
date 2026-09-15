# Python Work Order Service — Architecture

## Current scope

Phases 0–5 are implemented: full REST API, audit/webhook pipeline, background scheduler loop, and webhook delivery worker.

| Layer                                        | Status                                                            |
| -------------------------------------------- | ----------------------------------------------------------------- |
| API (`/api/v1/*`)                            | Active (~40 routes)                                               |
| Business services                            | Active                                                            |
| CRUD + SQLAlchemy models                     | Active                                                            |
| Auth (API key, internal token, vendor token) | Active                                                            |
| Audit events + webhook triggers              | Active on contract/work_order/invoice/payment mutations           |
| Background workers                           | Scheduler + webhook delivery (embedded or separate CLI processes) |
| Alembic `work_order` schema                  | Active (text IDs aligned with ORM)                                |

## High-level layout

```
Client
  │
  ▼
FastAPI app (main.py → create_application)
  │
  ├─ Middleware (CORS, rate limit, security headers)
  ├─ API router (/api/v1 → resource routers)
  ├─ Exception handlers + response_factory
  │
  ▼
Startup lifecycle (setup.py)
  ├─ PostgreSQL (create_all + pool)
  ├─ Redis client
  ├─ Webhook delivery worker
  └─ Scheduler loop (when WOM_SCHEDULER_ENABLED=true)
```

## Layering

```
api/v1/<resource>.py              → thin routers
  ↓ Depends(header validators, auth deps, async_get_db)
business/services/<x>_service.py  → orchestration and business rules
  ↓ uses crud singletons (+ EventsService, SchedulerService where needed)
crud/crud_<entity>.py             → DB access (CRUD* class + crud_* instance)
  ↓ uses models
models/<entity>.py                → SQLAlchemy ORM
schemas/<domain>.py               → Pydantic schemas + co-located enums
workers/
  cli/                            → run_scheduler_worker, run_webhook_worker
  schedulers/                     → scheduler_worker, webhook_delivery_worker
```

## Request flow (typical mutation)

```
1. HTTP request → /api/v1/<resource>
2. Middleware + auth dependency (API key / internal / vendor)
3. Router → Service method
4. CRUD write in same DB transaction
5. EventsService.record_and_dispatch → audit row + webhook delivery row
6. schedule_after_commit → enqueue webhook to background worker
7. Commit → JSON success response
```

## Scheduler behaviour

| Trigger                       | Behaviour                                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------------------ |
| `POST /scheduler/run`         | One-shot sweep under Postgres advisory lock                                                      |
| Background loop               | `WOM_SCHEDULER_INTERVAL_MINUTES` (default 60)                                                    |
| Contract create/update/delete | `SchedulerService.recompute_contract()` — cancel stale upcoming WOs, generate within lead window |
| Recurring templates           | Child instances generated; upcoming children cancelled when schedule changes                     |

## Application lifecycle

### Startup (non-test)

1. Load settings from environment
1. Connect PostgreSQL; `create_all` for ORM tables
1. Start webhook worker (recovers pending deliveries)
1. Start scheduler loop if enabled
1. Register routes, middleware, exception handlers

### Shutdown

1. Cancel scheduler task
1. Stop webhook worker
1. Close Redis and dispose Postgres pool

## Database sessions

| Use case       | Pattern                                    |
| -------------- | ------------------------------------------ |
| FastAPI routes | `db: AsyncSession = Depends(async_get_db)` |
| Workers        | `async with async_get_db_session() as db:` |

Side effects after commit: `schedule_after_commit(session, callback)`.

Apply Alembic when bootstrapping without `create_all`:

```bash
cd src && alembic upgrade head
```

Schema uses **text primary keys** (`api_key_*`, `contract_*`, `work_order_*`, …) consistent with CRUD `new_id()` helpers.

## Configuration

Primary settings: `src/app/core/config/app_config.py`

- App: `APP_NAME`, `ENVIRONMENT`, `PORT`, `CORS_ORIGINS`
- Postgres: `POSTGRES_URI`
- Redis: `REDIS_URL`, pool settings
- Work order: `WOM_INTERNAL_SERVICE_TOKEN`, `WOM_SCHEDULER_*`, R2 upload vars

## Adding a new audited entity

1. Schemas + model + crud + service + router
1. Call `EventsService.record_and_dispatch` after create/update/delete
1. Add entity to `TriggerEntity` enum if webhooks should match
1. Tests under `tests/v1/` and `tests/unit/`

## Technology stack

- FastAPI 0.115 + Uvicorn
- Python 3.13
- PostgreSQL (SQLAlchemy async + asyncpg)
- Redis (cache + rate limiting)
- Alembic migrations
- Pytest, Ruff, Black, pre-commit

## Related docs

- [README.md](README.md) — setup and route index
- [docs/PARITY_WITH_REFERENCE_BACKEND.md](docs/PARITY_WITH_REFERENCE_BACKEND.md) — comparison vs reference backend (routes, payloads, gaps)
- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow

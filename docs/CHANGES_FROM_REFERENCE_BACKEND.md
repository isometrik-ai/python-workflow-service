# Changes from Reference Backend

This document explains **what changed** when we rebuilt the work-order platform from the reference app at `order-management/backend` into this repository (`python-work-order-service`).

**Audience:** engineers, QA, and integrators joining the project.

**Reference baseline:** `/Users/3embed/Downloads/order-management/backend` (FastAPI + SQLAlchemy, tenant-scoped FM workflow).

**Last updated:** 2026-09-12

For a line-by-line parity matrix, see [PARITY_WITH_REFERENCE_BACKEND.md](PARITY_WITH_REFERENCE_BACKEND.md).

______________________________________________________________________

## 1. What this service is

This repo is a **modernized reimplementation** of the reference backend — not a byte-for-byte port.

We kept the same **product workflow**:

```text
Contracts → scheduled work orders → vendor execution → invoices → payments → audit + webhooks
```

We changed **how** the service is secured, scoped, stored, and exposed to clients.

| Goal                  | Approach                                         |
| --------------------- | ------------------------------------------------ |
| Multi-project tenancy | Every row has `tenant_id` + `project_id`         |
| Production-ready auth | API keys on all staff routes                     |
| Safer vendor access   | Hashed vendor tokens + dedicated vendor portal   |
| Cloud file storage    | S3/R2 keys + presigned upload URL                |
| Consistent API UX     | Standard response envelope on every endpoint     |
| Testability           | 98+ pytest cases, pre-commit, Alembic migrations |

______________________________________________________________________

## 2. Executive summary for teammates

| Question                                                   | Answer                                                                          |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Is the FM feature set complete vs reference?               | **Yes** (staff `/api/v1` scope)                                                 |
| Can we point the old frontend at this API without changes? | **No** — auth, envelope, enums, and types differ                                |
| Did we align JSON field names with reference?              | **Yes** for core entities (see §5)                                              |
| What's intentionally missing?                              | Public API (`/api/public/v1/*`), test-echo dev route                            |
| What's new vs reference?                                   | Vendor portal, presigned uploads, metrics, invoice DELETE, `project_id` scoping |

______________________________________________________________________

## 3. Architecture changes

These are **deliberate** design decisions, not gaps.

### 3.1 Tenancy and database

| Topic             | Reference                      | This service                                                                                  |
| ----------------- | ------------------------------ | --------------------------------------------------------------------------------------------- |
| Scope             | `tenant_id` only (query param) | `tenant_id` + **`project_id`** on every table                                                 |
| PostgreSQL schema | `public`                       | Dedicated schema **`fm`** (`POSTGRES_SCHEMA`; renamed from `work_order` in `20260913_000006`) |
| Primary keys      | Client may pass `id` on create | Server-generated (`work_order_*`, `contract_*`, …)                                            |
| Soft delete       | `deleted: bool`                | **`record_status`**: `active` / `deleted`                                                     |

### 3.2 Authentication

| Surface              | Reference                            | This service                                                |
| -------------------- | ------------------------------------ | ----------------------------------------------------------- |
| Staff FM routes      | Open + `?tenant_id=`                 | **`X-Api-Key`** (resolves tenant + project)                 |
| API key admin        | `/api/v1/settings/api-keys`          | `/api/v1/api-keys` + **`X-Internal-Token`** on create       |
| Vendor access        | Plaintext `vendor_token` on WO row   | **`X-Vendor-Token`** header + **`/api/v1/vendor/*`** routes |
| Public integrations  | Bearer `ats_…` on `/api/public/v1/*` | **Not built** — use staff API + API keys                    |
| Scheduler manual run | No auth                              | Internal token (all tenants) or API key (one tenant)        |

### 3.3 Data types and storage

| Topic                                    | Reference                            | This service                                                               |
| ---------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------- |
| Money                                    | Float columns (`Numeric`)            | Same **field names**, stored as **`BigInteger` minor units** (paise/cents) |
| Dates                                    | Often ISO strings in `String(32)`    | Native **`Date`** / **`DateTime(tz)`** (serialized as ISO in JSON)         |
| Files (photos, documents, invoice files) | Inline JSON / data-URL blobs         | **S3/R2 object keys** + `GET /upload/presigned-url`                        |
| Vendor token                             | Plaintext `vendor_token` column      | **`vendor_token_hash`** only; raw token shown once at WO create            |
| Timeline                                 | JSON array on `work_orders.timeline` | Same pattern                                                               |

### 3.4 API response shape

**Reference** returns raw Pydantic models:

```json
{ "id": "wo-1", "title": "Fix pump", "state": "Upcoming" }
```

**This service** wraps every response:

```json
{
  "status": "success",
  "message": "Resource retrieved successfully",
  "status_code": 200,
  "code": "SUCCESS",
  "data": { "id": "work_order_abc", "title": "Fix pump", "state": "upcoming" }
}
```

List endpoints add pagination metadata: `total`, `page`, `page_size`, `has_next`, `has_previous`.

### 3.5 Webhooks

| Topic              | Reference                                                           | This service                                                                            |
| ------------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Signature header   | `X-ATS-Signature: sha256=…`                                         | `X-Webhook-Signature` (HMAC-SHA256)                                                     |
| Delivery log shape | Denormalized (`work_order_id`, `work_order_title`, `payload`, `at`) | Normalized (`trigger_id`, `entity`, `request_payload`, `response_status`, `created_at`) |
| Retries            | 3 attempts, backoff                                                 | Same                                                                                    |

______________________________________________________________________

## 4. Routes: what we added, kept, and skipped

Base staff prefix: **`/api/v1`**. MCP: **`/api/mcp`**.

### 4.1 Fully implemented (matches reference staff scope)

- Asset categories, assets, form templates, contracts, work orders, invoices, payments
- Work order + invoice **timeline append** (`POST …/timeline`)
- Triggers (CRUD + `POST /triggers/{id}/test` + `GET /triggers/{id}`)
- Scheduler (`POST /scheduler/run`)
- Audit events, webhook deliveries, API call logs
- Custom fields, vendors (HoA CRM), business profile, PDF templates
- MCP JSON-RPC server (11 tools — same set as reference)

### 4.2 New in this service (not in reference backend)

| Module               | Routes                                                      | Why                                           |
| -------------------- | ----------------------------------------------------------- | --------------------------------------------- |
| **Vendor portal**    | `GET/PATCH /vendor/work-order`, `POST/GET /vendor/invoices` | Token-scoped vendor UI/API without staff keys |
| **Presigned upload** | `GET /upload/presigned-url`                                 | S3/R2 file uploads                            |
| **Metrics**          | `GET /metrics`                                              | Observability                                 |
| **Invoice DELETE**   | `DELETE /invoices/{id}`                                     | Soft-delete support reference lacked          |
| **API call logging** | Middleware on `POST /api/mcp` + `GET /api-call-logs`        | Reference had the table but no writer         |

### 4.3 Skipped from reference (by design)

| Module         | Reference routes               | Reason                                   |
| -------------- | ------------------------------ | ---------------------------------------- |
| **Public API** | `/api/public/v1/*` (11 routes) | Use `/api/v1/*` + API keys instead       |
| **Test echo**  | `POST/GET /api/v1/test-echo`   | Optional dev webhook helper — not ported |

### 4.4 Minor path differences

| Reference                   | This service                        |
| --------------------------- | ----------------------------------- |
| `GET /health` (app root)    | `GET /api/v1/health` (+ `/metrics`) |
| `/api/v1/settings/api-keys` | `/api/v1/api-keys`                  |

______________________________________________________________________

## 5. Field name alignment (migration changelog)

We renamed API/DB fields so JSON keys **match the reference** on core entities. Values/types may still differ (see §6).

### 5.1 Phase 1 — core entity renames (migration `20260912_000003`)

| Entity             | Old name(s) in this service                    | Now (matches reference)          |
| ------------------ | ---------------------------------------------- | -------------------------------- |
| **Assets**         | `facility_id`                                  | `location_id`                    |
| **Assets**         | `photo_paths`                                  | `photos`                         |
| **Assets**         | `document_paths`                               | `documents`                      |
| **Assets**         | `purchase_cost_minor`                          | `purchase_cost`                  |
| **Contracts**      | `value_minor`                                  | `value`                          |
| **Work orders**    | `assignee_name`                                | `assignee`                       |
| **Work orders**    | `estimated_cost_minor`                         | `estimated_cost`                 |
| **Invoices**       | `invoice_date`                                 | `date`                           |
| **Invoices**       | `subtotal_minor`, `tax_minor`, `total_minor`   | `subtotal`, `tax`, `total`       |
| **Invoices**       | `file_paths`                                   | `files` (+ kept `document` JSON) |
| **Payments**       | `amount_minor`, `payment_date`, `receipt_path` | `amount`, `date`, `receipt`      |
| **Form templates** | API key `form_schema`                          | `schema` (matches DB column)     |

### 5.2 Phase 2 — contracts documents (migration `20260912_000004`)

| Entity        | Change                                |
| ------------- | ------------------------------------- |
| **Contracts** | Column `document_paths` → `documents` |

### 5.3 Phase 3 — payload shape parity (migration `20260912_000005`)

| Entity               | Change                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------ |
| **Assets**           | `supplier_name` → `supplier`, `vendor_id` → `supplier_vendor_id`                                       |
| **Work orders**      | `recurring_days`: `smallint[]` (ISO 1–7) → `jsonb` string list (`"Monday"`, … or day-of-month strings) |
| **Audit events**     | `actor_name` → `actor`, `created_at` → `at`, dropped `actor_user_id`                                   |
| **WO timeline POST** | Added optional `from`, `to` fields (alongside `type`, `by`, `note`)                                    |
| **Audit list API**   | Added `source` query filter                                                                            |

### 5.4 Extra columns we kept (not in reference)

| Column              | Entity            | Purpose                           |
| ------------------- | ----------------- | --------------------------------- |
| `project_id`        | All tenant tables | Multi-project scoping             |
| `record_status`     | Most entities     | Explicit active/deleted lifecycle |
| `assignee_user_id`  | Work orders       | Link assignee to user id          |
| `vendor_token_hash` | Work orders       | Secure vendor portal access       |

______________________________________________________________________

## 6. Values that still differ (client-breaking)

Field **names** are aligned; these **values** are not:

### 6.1 Work order states

| Reference (UI strings) | This service  |
| ---------------------- | ------------- |
| `Upcoming`             | `upcoming`    |
| `In Progress`          | `in_progress` |
| `In Review`            | `in_review`   |
| `Closed`               | `completed`   |
| `Cancelled`            | `terminated`  |

There is no `cancelled` enum — scheduler cancellation flows use `terminated`.

### 6.2 Contract visit / payment frequency

Reference uses Title Case (`Quarterly`, `Half-yearly`). This service uses lowercase snake_case (`quarterly`, `half_yearly`).

We also added **`daily`** (visit) and **`one_time`** (payment frequency).

### 6.3 Money

Same JSON keys (`value`, `amount`, `subtotal`, …) but send/receive **integers in minor units** (e.g. ₹100.50 → `10050`), not floats.

### 6.4 Extra enum values

| Domain              | Extra values in this service     |
| ------------------- | -------------------------------- |
| Invoice status      | `resubmitted`                    |
| Work order source   | `recurring`                      |
| Work order priority | `urgent`                         |
| Payment status      | `pending`, `failed`, `voided`    |
| Payment method      | `cheque`, `cash`, `upi`, `other` |

______________________________________________________________________

## 7. Business logic — what stayed the same

These behaviours were ported and tested against reference intent:

- **Contract visit scheduling** — lazy work-order generation from `visit_frequency`, `auto_generate_lead_days`, `last_serviced_date`
- **Contract lifecycle** — recompute on create/update/delete; cancel upcoming WOs when contract is terminal or terms change
- **Recurring work orders** — template parent → child instances via background scheduler
- **Invoice workflow** — status transitions append timeline events; revision / approve / reject / paid flows
- **Payments** — recording payment marks invoice paid and adds WO timeline note
- **Audit + webhooks** — field-level diffs, trigger matching, async delivery worker with retries
- **HoA vendor CRM** — list/search/create via House of Apps SDK with httpx fallback
- **MCP tools** — same 11 tool names as reference public MCP server
- **Background workers** — scheduler loop + webhook worker (auto-start outside `test` env)

Default scheduler lead days when unset: **5** (same as reference runtime; reference create schema default is 7).

______________________________________________________________________

## 8. Database migrations

Alembic migrations under `src/migrations/versions/`:

| Revision          | Purpose                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| `20260912_000001` | Initial `work_order` schema                                                  |
| `20260912_000002` | Parity modules (custom fields, business profile, PDF templates, API keys, …) |
| `20260912_000003` | Core field name alignment                                                    |
| `20260912_000004` | Contract `documents` column rename                                           |
| `20260912_000005` | Supplier, recurring_days, audit actor/at                                     |
| `20260913_000006` | Rename PostgreSQL schema `work_order` → **`fm`**                             |

Apply with:

```bash
cd src && alembic upgrade head
```

______________________________________________________________________

## 9. Background workers

| Mode                                                | When                                                                           | How                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| **Embedded** (default local)                        | `WOM_EMBEDDED_SCHEDULER=true`, `WOM_EMBEDDED_WEBHOOK_WORKER=true`              | Workers run as asyncio tasks inside the API process |
| **Separate containers** (Docker Compose prod-style) | `WOM_EMBEDDED_*=false` on API + `scheduler-worker` / `webhook-worker` services | Same image, `python -m app.workers.cli.run_*`       |

Webhooks use a **DB outbox** (`webhook_deliveries` polled with `FOR UPDATE SKIP LOCKED`), not an in-memory queue — safe for multi-replica worker processes.

______________________________________________________________________

## 10. Quick integration guide for teammates

### 10.1 Calling staff APIs

```http
GET /api/v1/work-orders
X-Api-Key: <your-key>
```

Scope is resolved from the key (tenant + project). No bare `?tenant_id=` like reference.

### 10.2 Vendor portal

```http
GET /api/v1/vendor/work-order
X-Vendor-Token: <token-from-wo-create>
```

Token is returned **once** when a work order is created (also noted in timeline). Subsequent reads only expose `vendor_token_hash`.

### 10.3 MCP

```http
POST /api/mcp
Authorization: Bearer <api-key>
Content-Type: application/json

{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

### 10.4 Uploading files

1. `GET /api/v1/upload/presigned-url?file_name=…&path=…`
1. PUT file to returned URL
1. Store returned object key in `photos`, `documents`, or invoice `files`

Reference stored inline data-URL JSON instead — do not copy that pattern here.

______________________________________________________________________

## 11. Testing and quality

| Check      | Status                           |
| ---------- | -------------------------------- |
| pytest     | 98 tests passing                 |
| pre-commit | ruff, pylint, mdformat, etc.     |
| Coverage   | Domain services + v1 route tests |

Run locally:

```bash
PYTHONPATH=src pytest -q
pre-commit run --all-files
```

______________________________________________________________________

## 12. What to tell frontend / mobile teams

1. **Do not assume drop-in compatibility** with the reference API or old Postman collections.
1. **Parse the response envelope** — business data is always under `data`.
1. **Send money as integers** (minor units).
1. **Map work order states** — especially `Closed`→`completed`, `Cancelled`→`terminated`.
1. **Use lowercase frequency strings** on contracts.
1. **Auth is mandatory** — configure API keys per tenant/project.
1. **Vendor flows** should use `/api/v1/vendor/*`, not staff routes with a token query param.

If you need a compatibility shim later, see Option B in [PARITY_WITH_REFERENCE_BACKEND.md §10](PARITY_WITH_REFERENCE_BACKEND.md#10-recommended-paths-forward).

______________________________________________________________________

## 13. Related documents

| Document                                                             | Use when                                                |
| -------------------------------------------------------------------- | ------------------------------------------------------- |
| [PARITY_WITH_REFERENCE_BACKEND.md](PARITY_WITH_REFERENCE_BACKEND.md) | Detailed route/model/enum matrix and decision checklist |
| [README.md](../README.md)                                            | Setup, env vars, run commands                           |
| [PROJECT_FLOW.md](../PROJECT_FLOW.md)                                | Layering (router → service → crud → model)              |
| [CONTRIBUTING.md](../CONTRIBUTING.md)                                | Pre-commit, docstrings, PR workflow                     |

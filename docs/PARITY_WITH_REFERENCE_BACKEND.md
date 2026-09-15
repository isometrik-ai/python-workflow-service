# Parity: Work Order Service vs Reference Backend

This document compares **this repository** (`python-work-order-service`) with the reference implementation at:

`/Users/3embed/Downloads/order-management/backend`

Use it to decide whether to pursue **API compatibility**, **feature parity**, or **keep intentional differences**.

**Last reviewed:** 2026-09-12 (post payload-shape parity: supplier, recurring_days, audit actor/at, timeline from/to, audit source filter)

______________________________________________________________________

## 1. Executive summary

| Area                                                                            | Status                                                 |
| ------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Core FM workflow (contracts → work orders → invoices → payments)                | **Implemented**                                        |
| Staff `/api/v1` modules (assets → payments, triggers, logs, scheduler)          | **Implemented**                                        |
| Custom fields, vendors/HoA, business profile, PDF templates, MCP, API call logs | **Implemented**                                        |
| **API field names** vs reference (major entities)                               | **Mostly aligned** (see §5.8)                          |
| **Staff `/api/v1` route parity**                                                | **Yes**, except 3 optional reference-only items (§3.2) |
| Drop-in compatibility (responses, auth, enums, types)                           | **No**                                                 |

This service is a **modernized reimplementation**, not a clone. It adds multi-project tenancy, API-key auth, hashed vendor tokens, a dedicated vendor portal, S3/R2 presigned uploads, and a standard response envelope.

The reference backend adds **public API** (`/api/public/v1/*`) which we have **skipped by design** (use `/api/v1/*` + API keys instead).

______________________________________________________________________

## 2. Intentional architectural differences

These are design choices in this service, not oversights.

| Topic                        | Reference backend                                              | This service                                                                                                 |
| ---------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Tenancy**                  | `tenant_id` only (query param, default tenant)                 | `tenant_id` + **`project_id`** on every row                                                                  |
| **Staff API auth**           | No middleware on internal routes                               | **`X-Api-Key`** (+ scope headers) required                                                                   |
| **API key admin**            | `GET/POST/DELETE /api/v1/settings/api-keys`                    | `GET/POST/DELETE /api/v1/api-keys` + **`X-Internal-Token`** on create                                        |
| **Vendor access**            | Internal routes + `vendor_token` on WO + `X-ATS-Source` header | Dedicated **`/api/v1/vendor/*`** + **`X-Vendor-Token`**                                                      |
| **Money**                    | `Numeric(14,2)` floats                                         | Same field names (`value`, `amount`, …) stored as **`BigInteger`** (minor units)                             |
| **Dates**                    | Often ISO strings in `String(32)` columns                      | Native **`Date`** / **`DateTime(tz)`**                                                                       |
| **Files / uploads**          | Inline JSON / data-URL descriptors in DB                       | **S3/R2 object keys** + presigned URL endpoint                                                               |
| **Vendor token storage**     | Plaintext `vendor_token` on work order                         | **`vendor_token_hash`** (hash only)                                                                          |
| **Soft delete**              | `deleted: bool` + `deleted_at`                                 | **`record_status`** (`active` / `deleted`) + `deleted_at`                                                    |
| **Primary keys**             | Client may supply `id` on create                               | Server-generated text IDs (`contract_*`, `work_order_*`, …)                                                  |
| **API responses**            | Raw Pydantic models / simple pagination                        | Wrapped **`{ status, message, code, data }`** + list metadata                                                |
| **DB schema**                | Default `public`                                               | PostgreSQL schema **`fm`** (renamed from `work_order` in migration `20260913_000006`; `POSTGRES_SCHEMA` env) |
| **Webhook signature header** | `X-ATS-Signature: sha256=…`                                    | `X-Webhook-Signature` (HMAC-SHA256)                                                                          |

______________________________________________________________________

## 3. Route parity matrix

Base prefix: **`/api/v1`** (both). Reference also mounts **`/api/public/v1`** and **`/api/mcp`**.

### 3.1 Core domain — aligned or mostly aligned

| Resource           | Reference                     | This service                  | Gap                      |
| ------------------ | ----------------------------- | ----------------------------- | ------------------------ |
| Health             | `GET /health`                 | `GET /health`, `GET /metrics` | Extra metrics            |
| Asset categories   | CRUD                          | CRUD                          | ✓                        |
| Assets             | CRUD                          | CRUD                          | ✓                        |
| Form templates     | CRUD                          | CRUD                          | ✓                        |
| Contracts          | CRUD                          | CRUD                          | ✓                        |
| Work orders        | CRUD + `POST …/timeline`      | CRUD + `POST …/timeline`      | ✓                        |
| Invoices           | CRUD (no DELETE) + timeline   | CRUD + DELETE + timeline      | Extra DELETE             |
| Payments           | CRUD                          | CRUD                          | ✓                        |
| Triggers           | CRUD + test + **GET `/{id}`** | CRUD + test + GET `/{id}`     | ✓                        |
| Scheduler          | `POST /scheduler/run`         | `POST /scheduler/run`         | ✓                        |
| Audit events       | `GET /audit-events`           | `GET /audit-events`           | ✓                        |
| Webhook deliveries | `GET /webhook-deliveries`     | `GET /webhook-deliveries`     | ✓ (column shape differs) |
| API keys           | `/settings/api-keys`          | `/api-keys`                   | Path + auth differ       |

### 3.2 Reference only — not implemented here

| Module              | Routes                                                      |
| ------------------- | ----------------------------------------------------------- |
| **Public API**      | `/api/public/v1/work-orders`, contracts, invoices, payments |
| **Test echo (dev)** | `POST/GET /test-echo`                                       |

### 3.3 This service only — not in reference

| Module                | Routes                                                      |
| --------------------- | ----------------------------------------------------------- |
| **Vendor portal**     | `GET/PATCH /vendor/work-order`, `POST/GET /vendor/invoices` |
| **Presigned upload**  | `GET /upload/presigned-url`                                 |
| **Metrics**           | `GET /metrics`                                              |
| **Custom fields**     | CRUD `/custom-fields`                                       |
| **Vendors (HoA CRM)** | `GET /vendors`, `GET /vendors/search`, `POST /vendors`      |
| **Business profile**  | `GET/PUT /business-profile`                                 |
| **PDF templates**     | CRUD `/pdf-templates`                                       |
| **MCP server**        | `POST/GET /api/mcp` (JSON-RPC tools)                        |
| **API call logs**     | `GET /api-call-logs`                                        |

______________________________________________________________________

## 4. Authentication comparison

| Surface              | Reference                                | This service                                                      |
| -------------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| Internal FM API      | Open; `tenant_id` query param            | **`X-Api-Key`** resolves tenant/project (or headers + key lookup) |
| API key creation     | Body `{ name }` on settings route        | **`X-Internal-Token`** + `{ tenant_id, project_id, name }`        |
| Audit source / actor | `X-ATS-Source`, `X-ATS-Actor`            | Stored on audit rows as `source` / `actor`; headers not required  |
| Scheduler manual run | No special auth                          | Internal token (all tenants) **or** API key scope (single tenant) |
| Public integrations  | Bearer `ats_<hex>` on `/api/public/v1/*` | **Not implemented** (use API keys on `/api/v1/*` instead)         |

______________________________________________________________________

## 5. Model & payload field mapping

### 5.8 Aligned field names (2026-09-12)

These now **match** reference JSON keys on create/update/read:

| Entity           | Aligned fields                                                                          |
| ---------------- | --------------------------------------------------------------------------------------- |
| Assets           | `location_id`, `photos`, `documents`, `purchase_cost`, `supplier`, `supplier_vendor_id` |
| Contracts        | `value`, `documents`                                                                    |
| Work orders      | `assignee`, `estimated_cost`, `recurring_days`                                          |
| Invoices         | `date`, `subtotal`, `tax`, `total`, `document`, `files`                                 |
| Payments         | `amount`, `date`, `receipt`                                                             |
| Form templates   | `schema`                                                                                |
| Audit (read)     | `actor`, `at`                                                                           |
| WO timeline POST | `type`, `by`, `note`, `from`, `to`                                                      |

### 5.1 Work orders

| Reference (API/ORM)                                       | This service                | Notes                                                           |
| --------------------------------------------------------- | --------------------------- | --------------------------------------------------------------- |
| `assignee`                                                | `assignee`                  | ✓ Also: **`assignee_user_id`** (extra)                          |
| `estimated_cost` (float)                                  | `estimated_cost` (int)      | Same name; **integer minor units**                              |
| `vendor_token`                                            | `vendor_token_hash`         | Token shown once at creation; not stored plaintext              |
| `recurring_days: list[str]`                               | `recurring_days: list[str]` | ✓ Weekday names for weekly/fortnightly; day-of-month as strings |
| `scheduled_date`, `started_at`, `completed_at` as strings | Typed `date` / `datetime`   | Serialize as ISO in JSON                                        |
| `state: "Upcoming"` (Title Case)                          | `state: "upcoming"` (enum)  | See §6                                                          |
| Timeline append `from`, `to`                              | `from`, `to`                | ✓ Also `type`, `by`, `note`                                     |

### 5.2 Maintenance contracts

| Reference                        | This service                     | Notes                                                                            |
| -------------------------------- | -------------------------------- | -------------------------------------------------------------------------------- |
| `value` (float)                  | `value` (int)                    | Same name; **integer minor units**                                               |
| `documents: list`                | `documents: list[str]`           | S3 keys                                                                          |
| `visit_frequency: "Quarterly"`   | `visit_frequency: "quarterly"`   | See §6                                                                           |
| `payment_frequency: "Quarterly"` | `payment_frequency: "quarterly"` |                                                                                  |
| `status: draft`                  | `status: draft`                  | ✓ Also `active`, `expired`, `terminated`, `paused`                               |
| `auto_generate_lead_days`        | `auto_generate_lead_days`        | Scheduler default **5** when unset (both); reference create schema default **7** |

### 5.3 Invoices

| Reference                  | This service               | Notes                              |
| -------------------------- | -------------------------- | ---------------------------------- |
| `date`                     | `date`                     | ✓                                  |
| `subtotal`, `tax`, `total` | `subtotal`, `tax`, `total` | ✓ Same names; integer minor units  |
| `document{}`, `files[]`    | `document`, `files`        | ✓ Same keys; JSON shape may differ |
| —                          | `resubmitted` status       | Extra enum value                   |

### 5.4 Payments

| Reference                       | This service                       | Notes                            |
| ------------------------------- | ---------------------------------- | -------------------------------- |
| `amount`                        | `amount`                           | ✓ Same name; integer minor units |
| `date`                          | `date`                             | ✓                                |
| `receipt: dict`                 | `receipt`                          | ✓ Same key; JSON object          |
| `method` mostly `bank_transfer` | + `cheque`, `cash`, `upi`, `other` |                                  |
| `status` default `completed`    | + `pending`, `failed`, `voided`    |                                  |

### 5.5 Assets

| Reference                   | This service                | Notes |
| --------------------------- | --------------------------- | ----- |
| `photos`                    | `photos`                    | ✓     |
| `documents`                 | `documents`                 | ✓     |
| `location_id`               | `location_id`               | ✓     |
| `supplier`                  | `supplier`                  | ✓     |
| `supplier_vendor_id`        | `supplier_vendor_id`        | ✓     |
| `custom_field_values: dict` | `custom_field_values: dict` | ✓     |
| `purchase_cost`             | `purchase_cost`             | ✓     |

### 5.6 Form templates

| Reference | This service | Notes |
| --------- | ------------ | ----- |
| `schema`  | `schema`     | ✓     |

### 5.7 Webhook delivery log (read API)

Reference denormalizes: `work_order_id`, `work_order_title`, `actor`, `status_code`, `payload`, `at`.

This service normalizes: `trigger_id`, `entity`, `entity_id`, `request_payload`, `response_status`, `attempt`, `delivered`, `created_at`.

Same purpose; **list response fields differ**.

______________________________________________________________________

## 6. Enum and value mismatches (client-breaking)

### Work order `state`

| Reference (typical strings) | This service enum                         |
| --------------------------- | ----------------------------------------- |
| `Upcoming`                  | `upcoming`                                |
| `In Progress`               | `in_progress`                             |
| `In Review`                 | `in_review`                               |
| `Cancelled`                 | **`terminated`** (scheduler/cancel flows) |
| `Closed`                    | **`completed`**                           |

There is **no** `cancelled` state in this service — cancellation uses `terminated`.

### Visit / payment frequency (contracts)

| Reference (Title Case strings)                                           | This service (`VisitFrequency` / `PaymentFrequency`)                     |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `Weekly`, `Fortnightly`, `Monthly`, `Quarterly`, `Half-yearly`, `Yearly` | `weekly`, `fortnightly`, `monthly`, `quarterly`, `half_yearly`, `yearly` |
| —                                                                        | **`daily`** (extra)                                                      |
| —                                                                        | **`one_time`** payment frequency (extra)                                 |

### Invoice status

Both share: `submitted`, `revision_requested`, `approved`, `rejected`, `paid`.

This service adds: **`resubmitted`**.

### Work order source

Reference: `contract`, `ad_hoc`.

This service adds: **`recurring`**.

______________________________________________________________________

## 7. Business logic parity

| Behaviour                                                 | Reference | This service                |
| --------------------------------------------------------- | --------- | --------------------------- |
| Contract visit → auto-generate work orders                | ✓         | ✓                           |
| `recompute_contract` on contract CRUD                     | ✓         | ✓                           |
| Cancel upcoming WOs when contract terminal / terms change | ✓         | ✓                           |
| Recurring template → child work orders                    | ✓         | ✓                           |
| `cancel_recurring_children` on template change/delete     | ✓         | ✓                           |
| Invoice status change → timeline events                   | ✓         | ✓                           |
| Payment → mark invoice paid + work order timeline note    | ✓         | ✓                           |
| Audit event on mutations                                  | ✓         | ✓                           |
| Outbound webhooks (match entity + event)                  | ✓         | ✓                           |
| Webhook retries (3 attempts, backoff)                     | ✓         | ✓                           |
| Background scheduler loop                                 | ✓         | ✓ (`WOM_SCHEDULER_ENABLED`) |
| Background webhook worker                                 | ✓         | ✓                           |
| HoA vendor CRM proxy                                      | ✓         | ✓ (SDK or httpx fallback)   |
| PDF template engine                                       | ✓         | ✓ (CRUD; render not ported) |
| MCP tools                                                 | ✓         | ✓                           |
| Public API                                                | ✓         | ✗ (intentionally skipped)   |
| Push notifications                                        | ✗         | ✗                           |

______________________________________________________________________

## 8. Response shape

### Reference

- Single resource: returns `WorkOrderRead`, `ContractRead`, etc. directly.
- List: `{ total, page, page_size, total_pages, data: [...] }`.

### This service

- Single: `{ status, message, status_code, code, data: { ... } }`.
- List: same wrapper + `has_next`, `has_previous`.

Any frontend built for the reference app must be adapted for the envelope and field names.

______________________________________________________________________

## 9. Decision checklist

Use this when planning next work. Mark each row: **Keep** | **Adapter** | **Change service** | **Port from reference**.

### 9.1 API compatibility (breaking for existing clients)

- [ ] Unwrap responses or offer `?raw=true` compatibility mode
- [ ] Alias field names (`assignee` ↔ `assignee_name`, `date` ↔ `invoice_date`, …)
- [ ] Convert money floats ↔ `*_minor` integers at the boundary
- [ ] Map work order states (`Cancelled` ↔ `terminated`, `Closed` ↔ `completed`)
- [ ] Normalize visit frequency casing (`Quarterly` ↔ `quarterly`)
- [x] Align `recurring_days` representation (strings vs ISO ints)
- [ ] Expose `vendor_token` on read (security trade-off) or document one-time token flow

### 9.2 Missing routes (small scope)

- [x] Form templates: **PATCH**, **DELETE**
- [x] Triggers: **GET `/triggers/{id}`**
- [ ] API keys path alias `/settings/api-keys` (optional)

### 9.3 Missing modules (large scope)

- [x] Custom fields CRUD + asset `custom_field_values` integration
- [x] Vendors / HoA integration
- [x] Business profile
- [x] PDF templates
- [ ] Public API (`/api/public/v1/*`) — **skipped intentionally**
- [x] MCP server
- [x] API call log middleware + list endpoint

### 9.4 Keep as-is (recommended unless product says otherwise)

- [ ] `project_id` scoping
- [ ] API-key auth on staff routes
- [ ] `*_minor` money storage
- [ ] S3/R2 presigned uploads
- [ ] Hashed vendor tokens + dedicated vendor portal
- [ ] `record_status` soft delete pattern
- [ ] Standard response envelope

______________________________________________________________________

## 10. Recommended paths forward

### Option A — Stay on current API (document differences)

- Keep this doc as the contract for integrators.
- Update frontend/SDK to use this service’s field names and envelopes.
- **Effort:** Low (documentation + client updates).

### Option B — Compatibility adapter layer

- Add optional v0 routes or middleware that accept reference payloads and return reference-shaped JSON.
- Internal model stays unchanged.
- **Effort:** Medium–high; good for gradual migration.

### Option C — Full feature parity with reference

- Port missing modules (§9.3) plus fix route gaps (§9.2).
- Still requires Option B-style mapping unless reference clients are rewritten.
- **Effort:** High.

______________________________________________________________________

## 11. Related files in this repo

| Topic             | Location                                                                           |
| ----------------- | ---------------------------------------------------------------------------------- |
| Route index       | [README.md](../README.md)                                                          |
| Architecture      | [PROJECT_FLOW.md](../PROJECT_FLOW.md)                                              |
| ORM models        | `src/app/models/`                                                                  |
| Pydantic schemas  | `src/app/schemas/`                                                                 |
| Routers           | `src/app/api/v1/`                                                                  |
| Scheduler         | `src/app/business/services/scheduler_service.py`                                   |
| Events / webhooks | `src/app/business/services/events_service.py`, `src/app/workers/webhook_worker.py` |

______________________________________________________________________

## 12. Reference files (external)

| Topic             | Location                                               |
| ----------------- | ------------------------------------------------------ |
| ORM models        | `order-management/backend/app/models/models.py`        |
| CRUD schemas      | `order-management/backend/app/schemas/crud_schemas.py` |
| Routers           | `order-management/backend/app/routers/`                |
| Scheduler         | `order-management/backend/app/services/scheduler.py`   |
| Events / webhooks | `order-management/backend/app/services/events.py`      |

______________________________________________________________________

## 13. Final audit (2026-09-12)

Side-by-side review of **this repo** vs `/Users/3embed/Downloads/order-management/backend`.

### 13.1 Verdict

| Question                                                                                | Answer                                      |
| --------------------------------------------------------------------------------------- | ------------------------------------------- |
| Are all reference **staff modules** implemented?                                        | **Yes**                                     |
| Are all reference **HTTP routes** present?                                              | **Almost** — see §13.2                      |
| Are **payloads / DB columns** identical?                                                | **No** — intentional renames (§5, §6)       |
| Can a reference frontend call this API unchanged?                                       | **No** — envelope, auth, field names differ |
| Is **business logic** (scheduler, webhooks, contract recompute, recurring WOs) aligned? | **Yes**                                     |

### 13.2 Remaining route gaps (reference → this service)

| Item              | Reference                          | This service         | Action                                                 |
| ----------------- | ---------------------------------- | -------------------- | ------------------------------------------------------ |
| **Public API**    | 11 routes under `/api/public/v1/*` | Not implemented      | **Skipped intentionally** — use `/api/v1/*` + API keys |
| **Test echo**     | `POST/GET /api/v1/test-echo`       | Missing              | Optional dev helper for webhook testing                |
| **API keys path** | `/api/v1/settings/api-keys`        | `/api/v1/api-keys`   | Optional alias only                                    |
| **Health path**   | `GET /health` (root)               | `GET /api/v1/health` | Different mount; both exist                            |

Everything else in reference `/api/v1` is covered, including form-template PATCH/DELETE and trigger GET by id.

### 13.3 Extras in this service (not in reference)

| Module           | Notes                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Vendor portal    | `/api/v1/vendor/*` — replaces inline `vendor_token` + internal routes |
| Presigned upload | `/api/v1/upload/presigned-url`                                        |
| Metrics          | `/api/v1/metrics`                                                     |
| Invoice DELETE   | Reference has no DELETE on invoices                                   |
| `project_id`     | All models and scoped queries                                         |

### 13.4 Minor behavioural / query gaps (non-blocking)

| Area                        | Reference                                         | This service                                                         |
| --------------------------- | ------------------------------------------------- | -------------------------------------------------------------------- |
| **Form template list**      | Plain `list` (no pagination)                      | Paginated list envelope                                              |
| **Audit list filter**       | `source`, `limit` (max 500)                       | `entity`, `entity_id`, `source`, `page` / `page_size`                |
| **Webhook / api-call list** | `limit` (max 500)                                 | Paginated `page` / `page_size` (+ optional `limit` on api-call-logs) |
| **API call log writes**     | Table + list endpoint; **no writer in reference** | Middleware logs **POST `/api/mcp` only**                             |
| **Client-supplied IDs**     | Optional `id` on create for many resources        | Server-generated IDs only                                            |
| **Health path**             | `GET /health` (app root)                          | `GET /api/v1/health` (+ `/metrics`)                                  |

### 13.5 Model / table coverage

All reference tables have equivalents in schema **`fm`**:

| Reference table         | This service        | Column notes                                                                                 |
| ----------------------- | ------------------- | -------------------------------------------------------------------------------------------- |
| `asset_categories`      | ✓                   | + `project_id`, `record_status`                                                              |
| `custom_fields`         | ✓                   | + `project_id`, `record_status`                                                              |
| `assets`                | ✓                   | + `project_id`, `record_status`; field names aligned                                         |
| `form_templates`        | ✓                   | + `project_id`, `record_status`; API key `schema`                                            |
| `maintenance_contracts` | ✓                   | + `project_id`, `record_status`; money as integer minor units                                |
| `work_orders`           | ✓                   | + `assignee_user_id`, `project_id`, `record_status`; `vendor_token_hash` not plaintext token |
| `vendor_invoices`       | ✓                   | + `project_id`, `record_status`; money as integer minor units                                |
| `payments`              | ✓                   | + `project_id`, `record_status`; expanded status/method enums                                |
| `business_profile`      | ✓                   | + `project_id`                                                                               |
| `pdf_templates`         | ✓                   | Same shape; CRUD only (no server render in either codebase)                                  |
| `trigger_configs`       | ✓                   | + `project_id`, `record_status`                                                              |
| `audit_events`          | ✓                   | Same field names (`actor`, `at`); + `tenant_id`/`project_id`                                 |
| `webhook_deliveries`    | ✓                   | Denormalized WO fields dropped; normalized entity/trigger fields                             |
| `api_call_logs`         | ✓                   | + `project_id`; writer behaviour differs (§13.4)                                             |
| `api_keys`              | ✓                   | + `project_id`, `record_status`                                                              |
| `work_order_timeline`   | Unused in reference | Timeline stored in `work_orders.timeline` JSON (both)                                        |

### 13.6 Payload compatibility checklist

Use §5–§6 for field-by-field mapping. Highest-impact client differences:

1. Response **envelope** (`status`, `message`, `data`, …)
1. **Money** as integer minor units, not floats (field names match)
1. **Work order states** lowercase + `terminated`/`completed` vs reference `Cancelled`/`Closed`
1. **Visit/payment frequency** lowercase + `half_yearly` vs `Half-yearly`
1. **Auth**: `X-Api-Key` required; no bare `tenant_id` query param
1. **Vendor token**: one-time at WO create; not returned on subsequent reads (hash only)
1. **`project_id`** on every row and scoped queries

### 13.7 What “up to date” means here

- **Feature parity:** **Yes** for product scope (excluding public API by design).
- **Staff route parity:** **Yes** for `/api/v1`, minus optional test-echo and settings path alias.
- **Field name parity:** **Yes** for core entity JSON keys; remaining diffs are types, enums, envelope, and extra columns (`project_id`, `assignee_user_id`, `record_status`).
- **Wire compatibility:** **No** — response envelope, auth, enum casing, money types, soft-delete flag still differ.

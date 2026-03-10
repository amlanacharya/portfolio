# Service Contracts

Project root for implementation: `2026/advay`.

## FastAPI endpoints

### `GET /health`
- purpose: process liveness
- response shape:
  - `status`
  - `service`
  - `phase`
  - `environment`
- expected behavior:
  - always returns HTTP 200 when API process is up
  - must not depend on external services

### `GET /ready`
- purpose: dependency readiness summary
- response shape:
  - `status`
  - `service`
  - `phase`
  - `dependencies`
- `dependencies` keys:
  - `redis`
  - `postgres`
  - `neo4j`
- dependency entry shape:
  - `configured`
  - `available`
  - `detail`
- expected behavior:
  - returns HTTP 200 for full readiness
  - returns HTTP 503 when one or more dependencies are unavailable or not configured
  - must not perform business queries

### `POST /tools/get-kpi`
- purpose: deterministic KPI retrieval for Phase 2
- request shape:
  - `metric_name`
  - `period`
  - `filters`
- response shape:
  - `metric_name`
  - `value`
  - `unit`
  - `dataset_version`
  - `computed_at`
  - `freshness_status`
- expected behavior:
  - returns HTTP 200 when the KPI is supported and deterministically computed
  - returns HTTP 400 for unsupported metrics, unsupported filters, or invalid period shape
  - returns HTTP 422 when filtered `SUM(due_amount) = 0`
  - must use PostgreSQL-backed deterministic computation only

## Streamlit app
- purpose: Phase 1 shell only
- allowed behavior:
  - show project title
  - show phase scope
  - show static setup guidance
- disallowed behavior:
  - retrieval UI
  - KPI logic
  - agent workflow UI
  - advanced dashboard features

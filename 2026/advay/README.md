# Advay

Local-first NBFC enterprise decision platform built for architecture practice, portfolio depth, and production-style system design.

## Current status
- Phase 1 foundation setup: complete
- Phase 2 deterministic data backbone: complete
- Current working scope: deterministic KPI access over PostgreSQL for `collections_efficiency`

## Phase progress tracker

### Phase 1 completed
- FastAPI skeleton
- Streamlit skeleton
- config loader
- `/health` and `/ready`
- Redis cache adapter interface
- Postgres and Neo4j connection scaffolding

### Phase 2 completed
- canonical PostgreSQL schema for the KPI demo slice
- mock CSV seed data
- ingestion loader with contract validation
- dataset versioning and ingestion run tracking
- deterministic SQL-backed `get_kpi`
- dataset freshness check
- minimal API exposure through `POST /tools/get-kpi`

## What is implemented now
- deterministic KPI formula:
  - `collections_efficiency = (SUM(collected_amount) / SUM(due_amount)) * 100`
- KPI aggregation is executed in SQL over the filtered grain
- if filtered `SUM(due_amount) = 0`, the request fails explicitly
- mock dataset and schema runner for local Postgres
- test coverage for loader, freshness, KPI output, filter handling, and API response

## What is intentionally not implemented yet
- Pinecone
- embeddings
- Neo4j traversal logic
- LangGraph workflows
- policy retrieval
- memory
- advanced Streamlit dashboard features

## Project structure
- `advay_platform/`: application code
- `apps/api/`: FastAPI entrypoint
- `apps/ui/`: Streamlit shell
- `infra/sql/`: schema and seed SQL
- `infra/docker/`: local Postgres compose file
- `data/mock/`: mock source data and expected outputs
- `docs/`: blueprint, task docs, and contracts
- `tests/`: Phase 1 and Phase 2 checks

## Usage

### 1. Install dependencies
From the project root:

```powershell
python -m pip install -e .[dev]
```

### 2. Start local Postgres
From the project root:

```powershell
docker compose -f infra/docker/docker-compose.postgres.yml up -d
```

### 3. Configure Postgres DSN
PowerShell:

```powershell
$env:ADVAY_POSTGRES_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/advay"
```

### 4. Apply schema and seed data
From the project root:

```powershell
python -m advay_platform.loaders.seed
```

### 5. Run the API
From the project root:

```powershell
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Run the UI
From the project root:

```powershell
python -m streamlit run apps/ui/app.py
```

### 7. Run tests
From the project root:

```powershell
python -m pytest tests -q
```

Note:
- full Phase 2 integration checks require `ADVAY_POSTGRES_DSN` to be set
- without that DSN, database-backed tests will skip

## API behavior
- `GET /health`: returns HTTP 200 when the API process is alive
- `GET /ready`: returns HTTP 503 until Redis, Postgres, and Neo4j are configured and reachable
- `POST /tools/get-kpi`: returns deterministic PostgreSQL-backed results for `collections_efficiency`

Example request:

```json
{
  "metric_name": "collections_efficiency",
  "period": "2026-03-09",
  "filters": {
    "branch_code": "B001"
  }
}
```

## Current known follow-ups
- wrap the ingestion path in a single transaction
- select dataset version by requested period instead of latest version globally
- tighten ingestion validation for additional domain constraints where needed

## References
- `docs/blueprint.md`
- `docs/contracts/tool_contracts.md`
- `docs/contracts/data_contracts.md`
- `docs/contracts/service_contracts.md`
- `docs/tasks/phase_2_data_backbone.md`

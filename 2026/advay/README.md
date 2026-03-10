# Advay

Phase 2 deterministic data backbone for the local-first NBFC enterprise decision platform.

## Scope
- PostgreSQL schema for one deterministic KPI slice
- seed CSV load path
- `/health`, `/ready`, and `/tools/get-kpi`
- deterministic SQL-backed KPI tool
- dataset freshness check

## Setup
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Start local Postgres
From `C:\portfolio\2026\advay`:

```powershell
docker compose -f infra/docker/docker-compose.postgres.yml up -d
```

Set:

```powershell
$env:ADVAY_POSTGRES_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/advay"
```

## Apply schema and seed data
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m advay_platform.loaders.seed
```

## Run API
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

## Run UI
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m streamlit run apps/ui/app.py
```

## Run tests
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m pytest tests -q
```

## Current behavior
- `/health` should return HTTP 200.
- `/ready` returns HTTP 503 until Redis, Postgres, and Neo4j are configured and reachable.
- `POST /tools/get-kpi` returns deterministic PostgreSQL-backed results for `collections_efficiency`.
- Retrieval, LangGraph, Pinecone, embeddings, and document parsing are intentionally not implemented in Phase 2.

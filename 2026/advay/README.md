# Advay

Phase 1 foundation for the local-first NBFC enterprise decision platform.

## Scope
- FastAPI skeleton
- Streamlit skeleton
- config loader
- `/health` and `/ready`
- Redis cache adapter interface
- Postgres and Neo4j connector placeholders

## Setup
From `C:\portfolio\2026\advay`:

```powershell
C:\portfolio\.venv\Scripts\python.exe -m pip install -e .[dev]
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
- Retrieval, LangGraph, Pinecone, embeddings, and KPI logic are intentionally not implemented in Phase 1.

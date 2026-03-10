# Blueprint

Goal: Local-first NBFC enterprise decision platform.

Project root for all implementation paths: `2026/advay`.

Current active phase: Phase 2 deterministic data backbone.

Phase 2 scope:
- canonical PostgreSQL schema for one KPI demo
- seed/mock CSV data
- ingestion loader for mock CSV into canonical tables
- deterministic `get_kpi`
- dataset freshness check
- minimal API path for deterministic KPI access
- no Pinecone retrieval
- no LangGraph workflows

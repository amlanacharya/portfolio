# Phase 2 Data Backbone Task

## Phase goal
Implement the first trustworthy business-data path for the platform using deterministic PostgreSQL-backed computation.

## In scope
- canonical PostgreSQL schema for a minimal NBFC demo slice
- SQL DDL or migration scaffolding for:
  - datasets
  - dataset_versions
  - ingestion_runs
  - metric_definitions
  - metrics
- seed/mock CSV data for one KPI demo
- ingestion loader for mock CSV into canonical tables
- simple dataset freshness check
- deterministic `get_kpi` tool implementation
- API endpoint or internal service path to exercise `get_kpi`
- minimal validation that numeric outputs come from deterministic SQL results
- update docs if contracts or schema are clarified

## Suggested KPI demo
Use one KPI only, such as:
- collections_efficiency
or
- overdue_ratio

## Out of scope
- Pinecone
- embeddings
- document parsing
- Neo4j graph sync logic
- lineage traversal queries
- LangGraph workflows
- citation checker
- advanced Streamlit dashboard logic
- memory
- policy retrieval
- reranking

## Exit criteria
Phase 2 is complete only when:
1. mock data can be loaded into Postgres
2. one KPI can be computed deterministically
3. `get_kpi` returns value, unit, source/dataset version, and computed timestamp
4. freshness check works for the seeded dataset
5. no retrieval or agent orchestration logic has been added

## Implementation rule
If a requested change requires Pinecone, Neo4j traversal logic, LangGraph, embeddings, RAG, or policy retrieval, stop and report that it belongs to a later phase instead of implementing it.
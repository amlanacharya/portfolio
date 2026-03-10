# Project Phase Plan

## Phase 1 — Foundation setup
- FastAPI skeleton
- Streamlit skeleton
- config loader
- health/readiness endpoints
- Redis cache interface
- Postgres/Neo4j connector placeholders

## Phase 2 — Deterministic data backbone
- canonical Postgres schema
- seed/mock data
- ingestion contract loader
- get_kpi tool
- freshness checks

## Phase 3 — Document retrieval
- document parsing
- chunking
- embeddings
- Pinecone integration
- policy retrieval

## Phase 4 — Ontology + lineage
- Neo4j sync
- lineage traversal
- applicability queries

## Phase 5 — Orchestration + validation
- LangGraph
- verifier
- citation checker
- fallback logic
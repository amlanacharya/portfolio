# Phase 1 Setup Task

## Phase goal
Create only the platform foundation needed to start the application and verify dependency wiring.

## In scope
- FastAPI app skeleton
- Streamlit app skeleton
- config/settings loader
- `/health` endpoint
- `/ready` endpoint
- Redis cache adapter interface
- placeholder Postgres connector
- placeholder Neo4j connector
- package/module structure
- minimal startup wiring

## Out of scope
- Pinecone client or retrieval logic
- LangGraph state or workflows
- document parsing
- embeddings
- RAG pipelines
- business KPI logic
- SQL queries beyond connection tests
- Cypher queries beyond connection tests
- advanced Streamlit dashboard features
- Langfuse integration
- authentication/authorization beyond placeholders

## Exit criteria
Phase 1 is complete only when:
1. FastAPI starts successfully
2. Streamlit starts successfully
3. config loads from environment
4. `/health` returns OK
5. `/ready` returns dependency readiness summary
6. Redis interface exists and can be instantiated
7. Postgres and Neo4j connector placeholders exist
8. no retrieval, agent, or business logic has been implemented

## Implementation rule
If a requested change requires retrieval, business logic, LangGraph, Pinecone, or ontology queries, stop and report that it belongs to a later phase instead of implementing it.
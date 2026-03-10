# Runtime Config Contract

Project root for implementation: `2026/advay`.

## Environment variables

### Core
- `ADVAY_ENV`
  - default: `local`
  - allowed: `local`, `dev`, `test`, `demo`, `prod`
- `ADVAY_LOG_LEVEL`
  - default: `INFO`

### API
- `ADVAY_API_HOST`
  - default: `127.0.0.1`
- `ADVAY_API_PORT`
  - default: `8000`

### UI
- `ADVAY_UI_PORT`
  - default: `8501`

### Cache
- `ADVAY_REDIS_URL`
  - default: `redis://localhost:6379/0`

### Database placeholders
- `ADVAY_POSTGRES_DSN`
  - default: empty
  - rule: empty means Postgres is not configured yet
- `ADVAY_NEO4J_URI`
  - default: empty
  - rule: empty means Neo4j is not configured yet
- `ADVAY_NEO4J_USER`
  - default: empty
- `ADVAY_NEO4J_PASSWORD`
  - default: empty

## Phase 1 rules
- Missing database credentials must not crash app startup.
- Readiness checks may report `not_configured` or `unavailable`.
- No Pinecone, LangGraph, embedding, or Langfuse config is allowed in Phase 1.

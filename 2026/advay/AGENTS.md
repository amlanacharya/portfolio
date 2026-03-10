# AGENTS.md

## Project scope
- Project root is `2026/advay`.
- All Advay project artifacts must stay within this folder.
- Do not create Advay `apps/`, `services/`, `libs/`, `infra/`, or `docs/` at repo root.

## Required references before coding
- `2026/advay/docs/blueprint.md`
- `2026/advay/docs/contracts/tool_contracts.md`
- `2026/advay/docs/tasks/phase_2_data_backbone.md`

## Architecture guardrails
- Business-critical numbers must come from deterministic SQL/tools only.
- Neo4j is for lineage/dependency/ownership/policy applicability.
- Pinecone is retrieval-only, never canonical truth.
- Validation and authorization checks must run before final response composition.

## Safety
- Never hardcode secrets.
- Do not change DB schema without a migration plan.
- Do not silently weaken validation, auth, or audit behavior.

## Phase discipline
- The repository is currently in Phase 2 deterministic data backbone work.
- Allowed work in this phase: canonical Postgres schema, mock data loading, deterministic KPI tooling, freshness checks, and minimal API/service exposure for those paths.
- Do not implement Pinecone, embeddings, document parsing, Neo4j traversal logic, LangGraph workflows, policy retrieval, or memory in this phase.

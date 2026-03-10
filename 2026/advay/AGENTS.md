# AGENTS.md

## Project scope
- Project root is `2026/advay`.
- All Advay project artifacts must stay within this folder.
- Do not create Advay `apps/`, `services/`, `libs/`, `infra/`, or `docs/` at repo root.

## Required references before coding
- `2026/advay/docs/blueprint.md`
- `2026/advay/docs/contracts/tool_contracts.md`
- `2026/advay/docs/tasks/phase_1_setup.md`

## Architecture guardrails
- Business-critical numbers must come from deterministic SQL/tools only.
- Neo4j is for lineage/dependency/ownership/policy applicability.
- Pinecone is retrieval-only, never canonical truth.
- Validation and authorization checks must run before final response composition.

## Safety
- Never hardcode secrets.
- Do not change DB schema without a migration plan.
- Do not silently weaken validation, auth, or audit behavior.

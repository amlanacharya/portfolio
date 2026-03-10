# AGENTS.md

## Project identity
This repo builds a local-first NBFC enterprise decision platform.
Active project root for this platform is `2026/advay`.

Core stack:
- FastAPI
- Streamlit
- PostgreSQL
- Neo4j
- Pinecone
- LangGraph
- Langfuse
- Redis cache

## Non-negotiable architecture rules
- Business-critical numbers must come only from deterministic SQL/tools.
- LLMs may explain, summarize, compare, and synthesize, but not invent metrics.
- Neo4j is for lineage, dependency traversal, ownership, and policy applicability.
- Pinecone is retrieval-only, not canonical truth.
- Redis is the primary cache in local mode.
- Validation must run before final response composition.

## Working style
- Keep all Advay project files under `2026/advay/` (code, docs, config, tasks, contracts).
- Do not create Advay project files at `C:\portfolio` root.
- Read `2026/advay/docs/blueprint.md` and relevant `2026/advay/docs/contracts/*` before coding.
- Always use the OpenAI developer documentation MCP server when working with OpenAI APIs, Codex, LangGraph/OpenAI integrations, AGENTS.md, or MCP setup.
- Prefer small, reviewable changes.
- Do not invent schemas, contracts, or env vars.
- If a contract is missing, create/update the markdown spec first.
- Update docs when behavior changes.

## Safety
- Never hardcode secrets.
- Do not change DB schema without a migration plan.
- Do not weaken validation or auth silently.

## Output format
At the end of each task:
- summarize changes
- list files touched
- list checks run
- list risks / assumptions

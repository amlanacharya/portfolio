# Tool Contracts

## get_kpi
Inputs:
- metric_name: str
- period: str
- filters: dict

Supported `filters` keys in Phase 2:
- branch_code
- region
- product_type

Phase 2 period format:
- `YYYY-MM-DD`

Outputs:
- metric_name
- value
- unit
- dataset_version
- computed_at
- freshness_status

Rules:
- values must come from deterministic SQL or precomputed trusted source
- aggregation must be performed in SQL over the filtered grain
- if `SUM(due_amount) = 0`, fail explicitly instead of returning a computed value
- if freshness SLA is violated, freshness_status must indicate it
- if metric is unsupported, fail explicitly
- if a filter key is unsupported, fail explicitly

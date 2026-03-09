# Tool Contracts

## get_kpi
Inputs:
- metric_name: str
- period: str
- filters: dict

Outputs:
- metric_name
- value
- unit
- source_table
- computed_at

Rule:
- returned values must come from deterministic SQL or precomputed source

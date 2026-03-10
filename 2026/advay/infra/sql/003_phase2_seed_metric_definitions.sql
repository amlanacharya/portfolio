INSERT INTO metric_definitions (
    metric_name,
    unit,
    source_table,
    freshness_sla,
    supported_filters,
    description
)
VALUES (
    'collections_efficiency',
    'percent',
    'collections_daily',
    'daily',
    '["branch_code", "region", "product_type"]'::jsonb,
    'collections_efficiency = collected_amount / due_amount * 100'
)
ON CONFLICT (metric_name) DO UPDATE
SET
    unit = EXCLUDED.unit,
    source_table = EXCLUDED.source_table,
    freshness_sla = EXCLUDED.freshness_sla,
    supported_filters = EXCLUDED.supported_filters,
    description = EXCLUDED.description,
    active = TRUE;

CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset_loaded_at
ON dataset_versions (dataset_id, loaded_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_dataset_started_at
ON ingestion_runs (dataset_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collections_daily_business_date
ON collections_daily (business_date);

CREATE INDEX IF NOT EXISTS idx_collections_daily_branch_code
ON collections_daily (branch_code);

CREATE INDEX IF NOT EXISTS idx_collections_daily_region
ON collections_daily (region);

CREATE INDEX IF NOT EXISTS idx_collections_daily_product_type
ON collections_daily (product_type);

CREATE INDEX IF NOT EXISTS idx_collections_daily_dataset_version
ON collections_daily (dataset_version_id);

CREATE INDEX IF NOT EXISTS idx_metrics_metric_date
ON metrics (metric_name, business_date DESC);

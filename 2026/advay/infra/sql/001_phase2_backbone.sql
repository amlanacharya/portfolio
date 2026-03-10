CREATE TABLE IF NOT EXISTS datasets (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    freshness_sla TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id),
    version TEXT NOT NULL,
    source_file TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    business_date_min DATE,
    business_date_max DATE,
    UNIQUE (dataset_id, version)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id),
    dataset_version_id BIGINT REFERENCES dataset_versions(id),
    source_file TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS collections_daily (
    id BIGSERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    branch_code TEXT NOT NULL,
    region TEXT NOT NULL,
    product_type TEXT NOT NULL,
    due_accounts INTEGER NOT NULL,
    collected_accounts INTEGER NOT NULL,
    due_amount NUMERIC(14, 2) NOT NULL,
    collected_amount NUMERIC(14, 2) NOT NULL,
    dataset_version_id BIGINT NOT NULL REFERENCES dataset_versions(id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metric_definitions (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL,
    source_table TEXT NOT NULL,
    freshness_sla TEXT NOT NULL,
    supported_filters JSONB NOT NULL DEFAULT '[]'::jsonb,
    description TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL REFERENCES metric_definitions(metric_name),
    business_date DATE NOT NULL,
    value NUMERIC(14, 4) NOT NULL,
    unit TEXT NOT NULL,
    dataset_version_id BIGINT NOT NULL REFERENCES dataset_versions(id),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (metric_name, business_date, dataset_version_id)
);

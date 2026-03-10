from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from advay_platform.db.postgres import PostgresConnector
from advay_platform.config import get_settings
from advay_platform.loaders.seed import apply_phase2_sql, load_phase2_seed

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def expected_kpis() -> dict[str, object]:
    path = PROJECT_ROOT / "data" / "mock" / "expected_kpis.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def postgres_dsn() -> str:
    dsn = os.getenv("ADVAY_POSTGRES_DSN", "")
    if not dsn:
        pytest.skip("ADVAY_POSTGRES_DSN is required for Phase 2 integration tests")
    return dsn


@pytest.fixture
def configured_postgres(postgres_dsn: str) -> str:
    previous = os.getenv("ADVAY_POSTGRES_DSN")
    os.environ["ADVAY_POSTGRES_DSN"] = postgres_dsn
    get_settings.cache_clear()
    try:
        yield postgres_dsn
    finally:
        if previous is None:
            os.environ.pop("ADVAY_POSTGRES_DSN", None)
        else:
            os.environ["ADVAY_POSTGRES_DSN"] = previous
        get_settings.cache_clear()


@pytest.fixture
def postgres_connector(postgres_dsn: str) -> PostgresConnector:
    return PostgresConnector(postgres_dsn)


@pytest.fixture
def seeded_postgres(postgres_connector: PostgresConnector, configured_postgres: str) -> PostgresConnector:
    apply_phase2_sql(postgres_connector)
    postgres_connector.execute(
        """
        TRUNCATE TABLE metrics, collections_daily, ingestion_runs, dataset_versions, datasets
        RESTART IDENTITY CASCADE
        """
    )
    apply_phase2_sql(postgres_connector)
    load_phase2_seed(postgres_connector)
    return postgres_connector

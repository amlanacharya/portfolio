"""Phase 2 schema and seed runner."""

from __future__ import annotations

from pathlib import Path

from advay_platform.config import get_settings
from advay_platform.db.postgres import PostgresConnector
from advay_platform.loaders.collections_daily import CollectionsDailyLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_ROOT / "infra" / "sql"
DATA_DIR = PROJECT_ROOT / "data" / "mock"


def apply_phase2_sql(connector: PostgresConnector) -> None:
    for name in (
        "001_phase2_backbone.sql",
        "002_phase2_indexes.sql",
        "003_phase2_seed_metric_definitions.sql",
    ):
        connector.execute_script(SQL_DIR / name)


def load_phase2_seed(connector: PostgresConnector) -> dict[str, object]:
    return CollectionsDailyLoader(connector).load(DATA_DIR / "collections_daily.csv")


def main() -> None:
    connector = PostgresConnector(get_settings().postgres_dsn)
    apply_phase2_sql(connector)
    result = load_phase2_seed(connector)
    print(result)


if __name__ == "__main__":
    main()

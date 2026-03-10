"""Deterministic KPI tool implementation."""

from __future__ import annotations

from advay_platform.db.postgres import PostgresConnector
from advay_platform.services.freshness import get_freshness_status
from advay_platform.services.metrics import compute_collections_efficiency, get_metric_definition


def get_kpi(
    connector: PostgresConnector,
    metric_name: str,
    period: str,
    filters: dict[str, str],
) -> dict[str, object]:
    definition = get_metric_definition(connector, metric_name)
    if metric_name != "collections_efficiency":
        raise ValueError(f"metric_not_implemented:{metric_name}")

    computed = compute_collections_efficiency(connector, period, filters)
    freshness_status = get_freshness_status(connector, definition["source_table"])
    return {
        "metric_name": metric_name,
        "value": computed["value"],
        "unit": definition["unit"],
        "dataset_version": computed["dataset_version"],
        "computed_at": computed["computed_at"],
        "freshness_status": freshness_status,
    }

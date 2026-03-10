"""Deterministic SQL-backed KPI access."""

from __future__ import annotations

from datetime import date
from typing import Any

from advay_platform.db.postgres import PostgresConnector
from advay_platform.errors import (
    MetricComputationError,
    MetricNotFoundError,
    UnsupportedFilterError,
    UnsupportedMetricError,
)

SUPPORTED_FILTERS = {"branch_code", "region", "product_type"}


def _validate_period(period: str) -> date:
    return date.fromisoformat(period)


def _validate_filters(filters: dict[str, str]) -> dict[str, str]:
    unsupported = sorted(set(filters) - SUPPORTED_FILTERS)
    if unsupported:
        raise UnsupportedFilterError(f"unsupported_filters:{','.join(unsupported)}")
    return filters


def get_metric_definition(connector: PostgresConnector, metric_name: str) -> dict[str, Any]:
    row = connector.fetch_one(
        """
        SELECT metric_name, unit, source_table, freshness_sla, supported_filters
        FROM metric_definitions
        WHERE metric_name = %s AND active = TRUE
        """,
        (metric_name,),
    )
    if not row:
        raise UnsupportedMetricError(f"unsupported_metric:{metric_name}")
    return row


def get_latest_dataset_version(connector: PostgresConnector, dataset_name: str) -> dict[str, Any]:
    row = connector.fetch_one(
        """
        SELECT dv.id, dv.version
        FROM dataset_versions dv
        JOIN datasets d ON d.id = dv.dataset_id
        WHERE d.name = %s
        ORDER BY dv.loaded_at DESC, dv.id DESC
        LIMIT 1
        """,
        (dataset_name,),
    )
    if not row:
        raise MetricNotFoundError(f"dataset_version_missing:{dataset_name}")
    return row


def compute_collections_efficiency(
    connector: PostgresConnector,
    period: str,
    filters: dict[str, str],
) -> dict[str, Any]:
    business_date = _validate_period(period)
    validated_filters = _validate_filters(filters)
    dataset_version = get_latest_dataset_version(connector, "collections_daily")

    clauses = ["dataset_version_id = %s", "business_date = %s"]
    params: list[Any] = [dataset_version["id"], business_date]
    for key in ("branch_code", "region", "product_type"):
        if key in validated_filters:
            clauses.append(f"{key} = %s")
            params.append(validated_filters[key])

    query = f"""
        SELECT
            COUNT(*) AS row_count,
            SUM(due_amount) AS sum_due_amount,
            CASE
                WHEN SUM(due_amount) = 0 THEN NULL
                ELSE ROUND((SUM(collected_amount) / SUM(due_amount)) * 100, 4)
            END AS value,
            NOW() AS computed_at
        FROM collections_daily
        WHERE {' AND '.join(clauses)}
    """
    row = connector.fetch_one(query, tuple(params))
    if not row or int(row["row_count"] or 0) == 0:
        raise MetricNotFoundError("metric_value_not_found")
    if row["sum_due_amount"] == 0:
        raise MetricComputationError("zero_due_amount_sum:collections_efficiency")
    return {
        "value": float(row["value"]),
        "computed_at": row["computed_at"],
        "dataset_version": dataset_version["version"],
    }

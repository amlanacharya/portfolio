"""Dataset freshness evaluation for deterministic metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from advay_platform.db.postgres import PostgresConnector


def get_freshness_status(connector: PostgresConnector, dataset_name: str) -> str:
    row = connector.fetch_one(
        """
        SELECT MAX(dv.business_date_max) AS latest_business_date
        FROM dataset_versions dv
        JOIN datasets d ON d.id = dv.dataset_id
        WHERE d.name = %s
        """,
        (dataset_name,),
    )
    if not row or row["latest_business_date"] is None:
        return "unknown"

    latest_business_date = row["latest_business_date"]
    # Use UTC date to avoid local timezone rollovers making a daily dataset look stale.
    current_date = datetime.now(timezone.utc).date()
    if latest_business_date >= current_date - timedelta(days=1):
        return "fresh"
    return "stale"

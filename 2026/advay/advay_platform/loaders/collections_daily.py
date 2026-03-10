"""Loader for the Phase 2 collections daily mock dataset."""

from __future__ import annotations

import csv
from pathlib import Path

from advay_platform.db.postgres import PostgresConnector
from advay_platform.errors import ValidationError
from advay_platform.loaders.contracts import parse_record, validate_headers


class CollectionsDailyLoader:
    def __init__(self, connector: PostgresConnector) -> None:
        self.connector = connector

    def _ensure_dataset(self) -> int:
        self.connector.execute(
            """
            INSERT INTO datasets (name, source_type, freshness_sla)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            ("collections_daily", "csv", "daily"),
        )
        row = self.connector.fetch_one("SELECT id FROM datasets WHERE name = %s", ("collections_daily",))
        return int(row["id"])

    def _next_version(self, dataset_id: int) -> str:
        row = self.connector.fetch_one(
            "SELECT COUNT(*) AS version_count FROM dataset_versions WHERE dataset_id = %s",
            (dataset_id,),
        )
        return f"v{int(row['version_count']) + 1}"

    def load(self, csv_path: Path) -> dict[str, object]:
        dataset_id = self._ensure_dataset()
        version = self._next_version(dataset_id)
        run = self.connector.fetch_one(
            """
            INSERT INTO ingestion_runs (dataset_id, source_file, status)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (dataset_id, str(csv_path), "running"),
        )
        run_id = int(run["id"])
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                validate_headers(reader.fieldnames or [])
                records = [parse_record(row) for row in reader]

            business_dates = sorted(record.business_date for record in records)
            version_row = self.connector.fetch_one(
                """
                INSERT INTO dataset_versions (
                    dataset_id, version, source_file, row_count, business_date_min, business_date_max
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    dataset_id,
                    version,
                    str(csv_path),
                    len(records),
                    business_dates[0],
                    business_dates[-1],
                ),
            )
            dataset_version_id = int(version_row["id"])

            params = [
                (
                    record.business_date,
                    record.branch_code,
                    record.region,
                    record.product_type,
                    record.due_accounts,
                    record.collected_accounts,
                    record.due_amount,
                    record.collected_amount,
                    dataset_version_id,
                )
                for record in records
            ]
            self.connector.executemany(
                """
                INSERT INTO collections_daily (
                    business_date,
                    branch_code,
                    region,
                    product_type,
                    due_accounts,
                    collected_accounts,
                    due_amount,
                    collected_amount,
                    dataset_version_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params,
            )

            self.connector.execute(
                """
                INSERT INTO metrics (metric_name, business_date, value, unit, dataset_version_id)
                SELECT
                    'collections_efficiency',
                    business_date,
                    ROUND((SUM(collected_amount) / NULLIF(SUM(due_amount), 0)) * 100, 4),
                    'percent',
                    %s
                FROM collections_daily
                WHERE dataset_version_id = %s
                GROUP BY business_date
                ON CONFLICT (metric_name, business_date, dataset_version_id) DO UPDATE
                SET value = EXCLUDED.value, computed_at = NOW()
                """,
                (dataset_version_id, dataset_version_id),
            )

            self.connector.execute(
                """
                UPDATE ingestion_runs
                SET dataset_version_id = %s, row_count = %s, status = %s, completed_at = NOW()
                WHERE id = %s
                """,
                (dataset_version_id, len(records), "completed", run_id),
            )
            return {
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "dataset_version": version,
                "row_count": len(records),
            }
        except ValidationError:
            self.connector.execute(
                """
                UPDATE ingestion_runs
                SET status = %s, error_message = %s, completed_at = NOW()
                WHERE id = %s
                """,
                ("failed", "validation_error", run_id),
            )
            raise
        except Exception as exc:
            self.connector.execute(
                """
                UPDATE ingestion_runs
                SET status = %s, error_message = %s, completed_at = NOW()
                WHERE id = %s
                """,
                ("failed", str(exc), run_id),
            )
            raise

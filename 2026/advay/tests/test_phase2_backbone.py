from __future__ import annotations

from fastapi.testclient import TestClient

from advay_platform.api import create_app
from advay_platform.errors import MetricComputationError, ValidationError
from advay_platform.loaders.contracts import parse_record
from advay_platform.services.freshness import get_freshness_status
from advay_platform.tools.get_kpi import get_kpi


def test_contract_validation_rejects_zero_due_amount() -> None:
    row = {
        "business_date": "2026-03-09",
        "branch_code": "B001",
        "region": "north",
        "product_type": "personal_loan",
        "due_accounts": "10",
        "collected_accounts": "5",
        "due_amount": "0",
        "collected_amount": "1",
    }

    try:
        parse_record(row)
    except ValidationError as exc:
        assert str(exc) == "due_amount_must_be_positive"
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("expected ValidationError")


def test_get_kpi_returns_expected_value(seeded_postgres, expected_kpis) -> None:
    result = get_kpi(seeded_postgres, "collections_efficiency", "2026-03-09", {})

    assert result["value"] == expected_kpis["2026-03-09"]["all"]
    assert result["unit"] == "percent"
    assert result["dataset_version"] == "v1"
    assert result["freshness_status"] == "fresh"


def test_get_kpi_respects_filters(seeded_postgres, expected_kpis) -> None:
    branch_result = get_kpi(
        seeded_postgres,
        "collections_efficiency",
        "2026-03-09",
        {"branch_code": "B001"},
    )
    bike_result = get_kpi(
        seeded_postgres,
        "collections_efficiency",
        "2026-03-09",
        {"product_type": "bike_loan"},
    )

    assert branch_result["value"] == expected_kpis["2026-03-09"]["branch_code:B001"]
    assert bike_result["value"] == expected_kpis["2026-03-09"]["product_type:bike_loan"]


def test_freshness_status_is_reported(seeded_postgres) -> None:
    assert get_freshness_status(seeded_postgres, "collections_daily") == "fresh"


def test_get_kpi_fails_when_due_amount_sum_is_zero(seeded_postgres) -> None:
    dataset = seeded_postgres.fetch_one(
        "SELECT id FROM datasets WHERE name = %s",
        ("collections_daily",),
    )
    version = seeded_postgres.fetch_one(
        """
        INSERT INTO dataset_versions (
            dataset_id, version, source_file, row_count, business_date_min, business_date_max
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (dataset["id"], "v_zero_due", "manual_insert", 1, "2026-03-10", "2026-03-10"),
    )
    seeded_postgres.execute(
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
        ("2026-03-10", "B999", "west", "test_product", 1, 0, 0, 0, version["id"]),
    )

    try:
        get_kpi(seeded_postgres, "collections_efficiency", "2026-03-10", {})
    except MetricComputationError as exc:
        assert str(exc) == "zero_due_amount_sum:collections_efficiency"
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("expected MetricComputationError")


def test_get_kpi_api_returns_deterministic_payload(seeded_postgres, expected_kpis) -> None:
    client = TestClient(create_app())
    response = client.post(
        "/tools/get-kpi",
        json={"metric_name": "collections_efficiency", "period": "2026-03-09", "filters": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["value"] == expected_kpis["2026-03-09"]["all"]
    assert payload["unit"] == "percent"
    assert payload["dataset_version"] == "v1"


def test_get_kpi_api_fails_when_due_amount_sum_is_zero(seeded_postgres) -> None:
    dataset = seeded_postgres.fetch_one(
        "SELECT id FROM datasets WHERE name = %s",
        ("collections_daily",),
    )
    version = seeded_postgres.fetch_one(
        """
        INSERT INTO dataset_versions (
            dataset_id, version, source_file, row_count, business_date_min, business_date_max
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (dataset["id"], "v_zero_due_api", "manual_insert", 1, "2026-03-10", "2026-03-10"),
    )
    seeded_postgres.execute(
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
        ("2026-03-10", "B998", "west", "test_product", 1, 0, 0, 0, version["id"]),
    )

    client = TestClient(create_app())
    response = client.post(
        "/tools/get-kpi",
        json={"metric_name": "collections_efficiency", "period": "2026-03-10", "filters": {}},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "zero_due_amount_sum:collections_efficiency"

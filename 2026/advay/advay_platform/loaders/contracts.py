"""CSV contract validation for Phase 2 mock data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from advay_platform.errors import ValidationError


EXPECTED_COLUMNS = (
    "business_date",
    "branch_code",
    "region",
    "product_type",
    "due_accounts",
    "collected_accounts",
    "due_amount",
    "collected_amount",
)


@dataclass(frozen=True)
class CollectionsDailyRecord:
    business_date: date
    branch_code: str
    region: str
    product_type: str
    due_accounts: int
    collected_accounts: int
    due_amount: Decimal
    collected_amount: Decimal


def validate_headers(headers: list[str]) -> None:
    if tuple(headers) != EXPECTED_COLUMNS:
        raise ValidationError(f"invalid_columns:{headers}")


def parse_record(row: dict[str, str]) -> CollectionsDailyRecord:
    try:
        business_date = date.fromisoformat(row["business_date"])
    except ValueError as exc:
        raise ValidationError("invalid_business_date") from exc

    branch_code = row["branch_code"].strip()
    region = row["region"].strip()
    product_type = row["product_type"].strip()
    if not branch_code:
        raise ValidationError("branch_code_required")
    if not product_type:
        raise ValidationError("product_type_required")
    if not row["business_date"].strip():
        raise ValidationError("business_date_required")

    try:
        due_accounts = int(row["due_accounts"])
        collected_accounts = int(row["collected_accounts"])
        due_amount = Decimal(row["due_amount"])
        collected_amount = Decimal(row["collected_amount"])
    except (ValueError, InvalidOperation) as exc:
        raise ValidationError("invalid_numeric_value") from exc

    if due_amount <= 0:
        raise ValidationError("due_amount_must_be_positive")

    return CollectionsDailyRecord(
        business_date=business_date,
        branch_code=branch_code,
        region=region,
        product_type=product_type,
        due_accounts=due_accounts,
        collected_accounts=collected_accounts,
        due_amount=due_amount,
        collected_amount=collected_amount,
    )

# Data Contracts

## Mock dataset: collections_daily.csv
Columns:
- business_date: date
- branch_code: str
- region: str
- product_type: str
- due_accounts: int
- collected_accounts: int
- due_amount: float
- collected_amount: float

## KPI definition: collections_efficiency
Definition:
- collections_efficiency = collected_amount / due_amount * 100

Constraints:
- due_amount must be > 0 for valid KPI computation
- business_date is required
- branch_code is required
- product_type is required
- KPI aggregation must be executed in SQL over the filtered grain
- if filtered `SUM(due_amount) = 0`, the request must fail explicitly

Freshness SLA:
- daily

## Phase 2 seed expectations
Seed dataset must include:
- at least two business dates
- at least two branch codes
- at least two product types

Reference assertions for the main seeded day:
- overall collections_efficiency: 85.0
- `branch_code=B001`: 90.0
- `product_type=bike_loan`: 75.0

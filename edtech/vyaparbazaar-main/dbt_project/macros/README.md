# Macros

This directory contains reusable SQL snippets (macros) that can be used across multiple models.

## Available Macros

### Date Utils (`date_utils.sql`)

Macros for working with dates:

- `date_diff_in_days(start_date, end_date)`: Calculate the difference between two dates in days
- `is_recent_date(date_column, days=30)`: Check if a date is within the last N days
- `is_within_date_range(date_column, start_days_ago, end_days_ago)`: Check if a date is within a specific range
- `get_fiscal_year(date_column)`: Get the fiscal year for a date (April-March)
- `get_fiscal_quarter(date_column)`: Get the fiscal quarter for a date
- `get_season(date_column)`: Get the season for a date
- `is_weekend(date_column)`: Check if a date is a weekend
- `is_festival_season(date_column)`: Check if a date is during the festival season

### String Utils (`string_utils.sql`)

Macros for working with strings:

- `clean_string(column_name)`: Trim and lowercase a string
- `standardize_state_code(state_column)`: Convert state names to standard two-letter codes
- `extract_domain_from_email(email_column)`: Extract the domain from an email address
- `categorize_email_domain(email_column)`: Categorize email domains
- `format_phone_number(phone_column)`: Format a phone number
- `get_payment_method_category(payment_method_column)`: Categorize payment methods

## Usage Examples

### Using Date Utils

```sql
-- Calculate days since last order
SELECT
    customer_id,
    {{ date_diff_in_days('last_order_date', 'current_date()') }} as days_since_last_order
FROM customer_orders

-- Find recent customers
SELECT
    customer_id,
    last_order_date
FROM customer_orders
WHERE {{ is_recent_date('last_order_date', 60) }}

-- Get orders by fiscal quarter
SELECT
    order_id,
    order_date,
    {{ get_fiscal_quarter('order_date') }} as fiscal_quarter
FROM orders
```

### Using String Utils

```sql
-- Standardize state codes
SELECT
    customer_id,
    {{ standardize_state_code('customer_state') }} as state_code
FROM customers

-- Categorize email domains
SELECT
    customer_id,
    customer_email,
    {{ categorize_email_domain('customer_email') }} as email_provider
FROM customers

-- Format payment methods
SELECT
    order_id,
    payment_method,
    {{ get_payment_method_category('payment_method') }} as payment_category
FROM orders
```

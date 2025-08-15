# Custom Tests

This directory contains custom data quality tests that can be applied to models.

## Available Tests

### `assert_positive_values`

Tests that a column contains only positive values (greater than zero).

**Usage:**
```yaml
models:
  - name: orders
    columns:
      - name: order_amount
        tests:
          - assert_positive_values
```

### `assert_date_in_past`

Tests that a date column contains only dates in the past (not in the future).

**Usage:**
```yaml
models:
  - name: orders
    columns:
      - name: order_date
        tests:
          - assert_date_in_past
```

### `assert_valid_percentage`

Tests that a column contains valid percentage values (between 0 and 100).

**Usage:**
```yaml
models:
  - name: customer_metrics
    columns:
      - name: conversion_rate
        tests:
          - assert_valid_percentage
```

## Adding Tests to Models

You can add these custom tests to your models in the schema.yml files:

```yaml
version: 2

models:
  - name: stg_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: order_amount
        tests:
          - assert_positive_values
      - name: order_date
        tests:
          - assert_date_in_past

  - name: customer_metrics
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: conversion_rate
        tests:
          - assert_valid_percentage
```

## Running Tests

To run all tests:

```bash
dbt test
```

To run tests for a specific model:

```bash
dbt test -m model_name
```

To run a specific test:

```bash
dbt test -m model_name --select test_type:test_name
```

For example:

```bash
dbt test -m stg_orders --select test_type:assert_positive_values
```

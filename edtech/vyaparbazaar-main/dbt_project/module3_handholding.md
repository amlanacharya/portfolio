# Module 3: Advanced Data Modeling Techniques 🚀

Welcome to Module 3 of the VyaparBazaar Analytics Internship Camp! In this module, we'll dive deeper into advanced data modeling techniques that will help you build more sophisticated, efficient, and maintainable data transformations. Building on the fundamentals from Module 2, we'll explore how to create complex models that deliver valuable business insights.

## 🎯 Learning Objectives

By the end of this module, you will be able to:
- Create advanced modular SQL using CTEs for complex transformations
- Build intermediate models that join and aggregate data effectively
- Apply dimensional modeling concepts (facts and dimensions)
- Optimize model performance with materialization strategies
- Implement advanced testing approaches for data quality

## 🧩 Advanced CTEs and Modular SQL

### The Power of CTEs in Complex Transformations

Common Table Expressions (CTEs) are a powerful tool for breaking down complex SQL into manageable, readable chunks. In Module 2, you learned the basics of CTEs. Now, let's explore more advanced techniques:

#### 1. CTE Chaining for Progressive Transformations

```sql
with 
-- Step 1: Get base customer data
customers as (
    select * from {{ ref('stg_customers') }}
),

-- Step 2: Get order data
orders as (
    select * from {{ ref('stg_orders') }}
),

-- Step 3: Calculate order metrics per customer
customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        count(o.order_id) as order_count,
        min(o.order_purchase_timestamp) as first_order_date,
        max(o.order_purchase_timestamp) as last_order_date,
        {{ datediff('min(o.order_purchase_timestamp)', 'max(o.order_purchase_timestamp)', 'day') }} as customer_lifetime_days
    from customers c
    left join orders o on c.customer_id = o.customer_id
    group by 1, 2
),

-- Step 4: Calculate recency, frequency metrics
customer_metrics as (
    select
        customer_id,
        customer_unique_id,
        order_count,
        first_order_date,
        last_order_date,
        customer_lifetime_days,
        {{ datediff('last_order_date', 'current_timestamp()', 'day') }} as days_since_last_order,
        case
            when order_count = 0 then 'No Orders'
            when order_count = 1 then 'Single Order'
            when order_count > 1 and days_since_last_order <= 30 then 'Active Repeat'
            when order_count > 1 and days_since_last_order > 30 then 'Inactive Repeat'
        end as customer_status
    from customer_orders
)

-- Final selection
select * from customer_metrics
```

#### 2. Self-Referencing CTEs

Sometimes you need to reference a CTE within itself, particularly for hierarchical data:

```sql
with recursive category_hierarchy as (
    -- Base case: top-level categories
    select
        category_id,
        category_name,
        parent_category_id,
        1 as level,
        category_name as path
    from {{ ref('stg_categories') }}
    where parent_category_id is null
    
    union all
    
    -- Recursive case: child categories
    select
        c.category_id,
        c.category_name,
        c.parent_category_id,
        h.level + 1 as level,
        h.path || ' > ' || c.category_name as path
    from {{ ref('stg_categories') }} c
    inner join category_hierarchy h on c.parent_category_id = h.category_id
)

select * from category_hierarchy
```

#### 3. Reusable CTEs with Macros

For complex transformations that you use repeatedly, consider creating macros:

```sql
{% macro get_customer_order_metrics() %}
    select
        customer_id,
        count(order_id) as order_count,
        sum(order_total) as total_spend,
        avg(order_total) as avg_order_value,
        min(order_purchase_timestamp) as first_order_date,
        max(order_purchase_timestamp) as last_order_date
    from {{ ref('stg_orders') }}
    group by 1
{% endmacro %}

-- Usage in a model
with customer_metrics as (
    {{ get_customer_order_metrics() }}
)

select * from customer_metrics
```

## 📊 Intermediate Models and Complex Aggregations

Intermediate models serve as the bridge between staging models and business-ready mart models. They typically involve:

1. Joining multiple staging models
2. Performing complex calculations
3. Creating reusable metrics for downstream models

### Example: Building a Customer Behavior Intermediate Model

```sql
-- models/intermediate/int_customer_behavior.sql
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
),

order_payments as (
    select
        order_id,
        sum(payment_value) as order_total,
        array_agg(payment_type) as payment_methods
    from payments
    group by 1
),

customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        count(o.order_id) as order_count,
        sum(op.order_total) as total_spend,
        avg(op.order_total) as avg_order_value,
        min(o.order_purchase_timestamp) as first_order_date,
        max(o.order_purchase_timestamp) as last_order_date,
        {{ datediff('min(o.order_purchase_timestamp)', 'max(o.order_purchase_timestamp)', 'day') }} as customer_lifetime_days,
        {{ datediff('max(o.order_purchase_timestamp)', 'current_timestamp()', 'day') }} as days_since_last_order
    from customers c
    left join orders o on c.customer_id = o.customer_id
    left join order_payments op on o.order_id = op.order_id
    group by 1, 2, 3, 4
)

select * from customer_orders
```

### Advanced Aggregation Techniques

#### 1. Window Functions for Time-Based Analysis

```sql
select
    customer_id,
    order_id,
    order_purchase_timestamp,
    order_total,
    sum(order_total) over (partition by customer_id order by order_purchase_timestamp) as cumulative_spend,
    lag(order_purchase_timestamp) over (partition by customer_id order by order_purchase_timestamp) as previous_order_date,
    {{ datediff('lag(order_purchase_timestamp) over (partition by customer_id order by order_purchase_timestamp)', 
                'order_purchase_timestamp', 
                'day') }} as days_since_previous_order
from {{ ref('stg_orders') }}
```

#### 2. Pivot Tables with Jinja

```sql
{% set payment_methods = ['credit_card', 'debit_card', 'upi', 'cod', 'voucher'] %}

select
    order_id,
    {% for payment_method in payment_methods %}
    sum(case when payment_type = '{{ payment_method }}' then payment_value else 0 end) as {{ payment_method }}_amount,
    {% endfor %}
    sum(payment_value) as total_amount
from {{ ref('stg_payments') }}
group by 1
```

## 🏗️ Dimensional Modeling Concepts

Dimensional modeling is a technique used to structure data in a way that's intuitive for business users and optimized for analytical queries.

### Facts and Dimensions

#### Fact Tables
- Contain **measurements** or **metrics** of business processes
- Examples: orders, sales, page views
- Usually have foreign keys to dimension tables

#### Dimension Tables
- Contain **descriptive attributes** used for filtering and grouping
- Examples: customers, products, dates
- Usually have a primary key referenced by fact tables

### Example: Creating a Date Dimension

```sql
-- models/dimensions/dim_date.sql
{{ config(materialized='table') }}

with date_spine as (
    {{ dbt_utils.date_spine(
        start_date="cast('2018-01-01' as date)",
        end_date="cast('2023-12-31' as date)",
        datepart="day"
    ) }}
),

dates as (
    select
        date_day as date_key,
        date_day as calendar_date,
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(quarter from date_day) as quarter,
        extract(dayofweek from date_day) as day_of_week,
        extract(dayofyear from date_day) as day_of_year,
        case
            when extract(dayofweek from date_day) in (0, 6) then true
            else false
        end as is_weekend,
        {{ is_festival_season('date_day') }} as is_festival_season
    from date_spine
)

select * from dates
```

### Example: Creating an Order Facts Table

```sql
-- models/facts/fct_orders.sql
{{ config(materialized='table') }}

with orders as (
    select * from {{ ref('stg_orders') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
),

order_payments as (
    select
        order_id,
        sum(payment_value) as order_total,
        array_agg(payment_type) as payment_methods
    from payments
    group by 1
),

order_facts as (
    select
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp as order_date,
        o.order_status,
        op.order_total,
        count(oi.order_item_id) as item_count,
        sum(oi.price) as items_price,
        sum(oi.freight_value) as freight_value
    from orders o
    left join order_items oi on o.order_id = oi.order_id
    left join order_payments op on o.order_id = op.order_id
    group by 1, 2, 3, 4, 5
)

select * from order_facts
```

## ⚡ Performance Optimization Techniques

As your dbt project grows, optimizing performance becomes increasingly important. Here are some techniques to improve the efficiency of your models:

### 1. Choosing the Right Materialization

dbt offers several materialization options:

- **View**: Fastest to build, but can be slow to query
- **Table**: Slower to build, but faster to query
- **Incremental**: Only processes new or changed data
- **Ephemeral**: Exists only during the build process

Choose based on:
- How frequently the data changes
- How frequently the model is queried
- The size of the dataset
- The complexity of the transformations

### 2. Incremental Models for Large Datasets

For large datasets that are frequently updated, incremental models can significantly improve build times:

```sql
-- models/staging/stg_clickstream.sql
{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_clickstream') }}
    {% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
    {% endif %}
),

renamed as (
    select
        event_id,
        customer_id,
        event_timestamp,
        event_type,
        page_type,
        device,
        browser,
        operating_system,
        session_id
    from source
)

select * from renamed
```

### 3. Partitioning and Clustering

For very large tables, consider partitioning and clustering:

```sql
-- models/marts/customer_marts/customer_orders.sql
{{
    config(
        materialized='table',
        partition_by={
            "field": "order_date",
            "data_type": "timestamp",
            "granularity": "month"
        },
        cluster_by=["customer_id", "order_status"]
    )
}}

select
    order_id,
    customer_id,
    order_date,
    order_status,
    order_total
from {{ ref('fct_orders') }}
```

## 🧪 Advanced Testing Strategies

Testing is crucial for ensuring data quality. Let's explore some advanced testing strategies:

### 1. Custom Generic Tests

Create reusable tests that can be applied to multiple models:

```sql
-- tests/generic/test_values_in_range.sql
{% test values_in_range(model, column_name, min_value, max_value) %}

select
    {{ column_name }} as failing_value
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}

{% endtest %}
```

Usage in schema.yml:
```yaml
models:
  - name: fct_orders
    columns:
      - name: order_total
        tests:
          - values_in_range:
              min_value: 0
              max_value: 10000
```

### 2. Data Quality Tests with dbt-expectations

The dbt-expectations package provides advanced testing capabilities:

```yaml
models:
  - name: stg_customers
    columns:
      - name: customer_zip_code_prefix
        tests:
          - dbt_expectations.expect_column_values_to_match_regex:
              regex: '^[0-9]{5}$'
      - name: customer_state
        tests:
          - dbt_expectations.expect_column_values_to_be_in_set:
              value_set: ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'GO', 'MA', 'PA', 'BA', 'ES']
```

### 3. Row-Count Tests

Ensure your models have the expected number of rows:

```yaml
models:
  - name: dim_customers
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: ref('stg_customers')
```

## 🧠 Hands-on Exercises

Now that you understand these advanced concepts, it's time to apply them! Check out the [Module 3 Exercises](module3_exercises.md) document for detailed instructions on practical exercises.

## 📚 Additional Resources

- [dbt Discourse Community](https://discourse.getdbt.com/)
- [dbt-utils Package Documentation](https://github.com/dbt-labs/dbt-utils)
- [dbt-expectations Package Documentation](https://github.com/calogica/dbt-expectations)
- [Dimensional Modeling Techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/)
- [DuckDB Performance Optimization](https://duckdb.org/docs/sql/query_optimization)

## 🎯 Next Steps

In Module 4, we'll explore advanced analytics techniques, including creating metrics, building dashboards, and integrating with BI tools.

Happy modeling! 🚀

# 🏗️ Module 3: Advanced Data Modeling Techniques

## Building Sophisticated Analytics Models with dbt

---

## 🎯 Learning Objectives

By the end of this module, you will be able to:

- Create advanced modular SQL using CTEs
- Build intermediate models with complex aggregations
- Apply dimensional modeling concepts
- Optimize model performance
- Implement advanced testing strategies

---

## 🧩 Advanced CTEs and Modular SQL

### Breaking Down Complex Transformations

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

-- Step 3: Calculate order metrics
customer_orders as (
    select
        c.customer_id,
        count(o.order_id) as order_count,
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date
    from customers c
    left join orders o on c.customer_id = o.customer_id
    group by 1
)

select * from customer_orders
```

---

## 🧩 Self-Referencing CTEs

### For Hierarchical Data

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
    inner join category_hierarchy h 
        on c.parent_category_id = h.category_id
)
```

---

## 🧩 Reusable CTEs with Macros

```sql
{% macro get_customer_order_metrics() %}
    select
        customer_id,
        count(order_id) as order_count,
        sum(order_total) as total_spend,
        avg(order_total) as avg_order_value,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date
    from {{ ref('stg_orders') }}
    group by 1
{% endmacro %}

-- Usage in a model
with customer_metrics as (
    {{ get_customer_order_metrics() }}
)
```

---

## 📊 Intermediate Models

### The Bridge Between Staging and Marts

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
        sum(payment_value) as order_total
    from payments
    group by 1
),

customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        count(o.order_id) as order_count,
        sum(op.order_total) as total_spend,
        avg(op.order_total) as avg_order_value
    from customers c
    left join orders o on c.customer_id = o.customer_id
    left join order_payments op on o.order_id = op.order_id
    group by 1, 2
)
```

---

## 📊 Window Functions for Time-Based Analysis

```sql
select
    customer_id,
    order_id,
    order_date,
    order_total,
    sum(order_total) over (
        partition by customer_id 
        order by order_date
    ) as cumulative_spend,
    
    lag(order_date) over (
        partition by customer_id 
        order by order_date
    ) as previous_order_date,
    
    datediff(
        day,
        lag(order_date) over (
            partition by customer_id 
            order by order_date
        ),
        order_date
    ) as days_since_previous_order
```

---

## 📊 Pivot Tables with Jinja

```sql
{% set payment_methods = ['credit_card', 'debit_card', 'upi', 'cod', 'voucher'] %}

select
    order_id,
    {% for payment_method in payment_methods %}
    sum(case 
        when payment_type = '{{ payment_method }}' 
        then payment_value 
        else 0 
    end) as {{ payment_method }}_amount,
    {% endfor %}
    sum(payment_value) as total_amount
from {{ ref('stg_payments') }}
group by 1
```

---

## 🏗️ Dimensional Modeling

### Facts and Dimensions

![Dimensional Modeling](https://i.imgur.com/XYZ123.png)

- **Fact Tables**: Measurements of business processes
  - Examples: orders, sales, page views
  - Contains foreign keys to dimension tables

- **Dimension Tables**: Descriptive attributes
  - Examples: customers, products, dates
  - Contains primary keys referenced by fact tables

---

## 🏗️ Creating a Date Dimension

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
        case
            when extract(dayofweek from date_day) in (0, 6) then true
            else false
        end as is_weekend
    from date_spine
)
```

---

## 🏗️ Creating an Order Facts Table

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

order_facts as (
    select
        o.order_id,
        o.customer_id,
        o.order_date,
        o.order_status,
        count(oi.order_item_id) as item_count,
        sum(oi.price) as items_price,
        sum(oi.freight_value) as freight_value
    from orders o
    left join order_items oi on o.order_id = oi.order_id
    group by 1, 2, 3, 4
)
```

---

## ⚡ Performance Optimization

### Choosing the Right Materialization

- **View**: Fastest to build, but can be slow to query
- **Table**: Slower to build, but faster to query
- **Incremental**: Only processes new or changed data
- **Ephemeral**: Exists only during the build process

Choose based on:
- How frequently the data changes
- How frequently the model is queried
- The size of the dataset
- The complexity of the transformations

---

## ⚡ Incremental Models for Large Datasets

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
        session_id
    from source
)
```

---

## ⚡ Partitioning and Clustering

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
```

---

## 🧪 Advanced Testing Strategies

### Custom Generic Tests

```sql
-- tests/generic/test_values_in_range.sql
{% test values_in_range(model, column_name, min_value, max_value) %}

select
    {{ column_name }} as failing_value
from {{ model }}
where {{ column_name }} < {{ min_value }} 
   or {{ column_name }} > {{ max_value }}

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

---

## 🧪 Data Quality Tests with dbt-expectations

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
              value_set: ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC']
```

---

## 🧪 Row-Count Tests

```yaml
models:
  - name: dim_customers
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: ref('stg_customers')
```

---

## 🧠 Hands-on Exercises

### Exercise 3.1: Create a Date Dimension Model
- Build a comprehensive date dimension with fiscal periods, seasons, and holidays

### Exercise 3.2: Build an Order Facts Model
- Create a fact table joining orders, items, and payments

### Exercise 3.3: Create an Incremental Clickstream Model
- Implement an efficient incremental model for event data

### Exercise 3.4: Build a Customer Behavior Mart Model
- Create a business-focused mart with RFM segmentation

### Exercise 3.5: Implement Advanced Testing
- Add custom tests and dbt-expectations tests

---

## 🚀 Real-world Impact

- **Faster Analytics**: Optimized models for quicker insights
- **Better Data Quality**: Comprehensive testing ensures reliability
- **Business-Ready Data**: Dimensional models are intuitive for analysts
- **Scalable Processing**: Incremental models handle large datasets efficiently
- **Maintainable Code**: Modular SQL is easier to understand and update

---

## 🎯 Key Takeaways

1. **Advanced CTEs** make complex transformations manageable
2. **Window functions** enable sophisticated time-based analysis
3. **Dimensional modeling** creates intuitive business-ready data
4. **Performance optimization** ensures efficient processing
5. **Advanced testing** maintains data quality

---

## 🔮 What's Next?

In **Module 4**, we'll explore:

- Advanced analytics techniques
- Creating metrics
- Building dashboards
- Integrating with BI tools

---

## 🙋 Questions?

Let's discuss!

---

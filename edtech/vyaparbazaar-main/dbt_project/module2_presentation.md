# 🧩 Module 2: Data Transformation Fundamentals

## SQL, Jinja, Macros, Sources, and Testing in dbt

---

## 🎯 Learning Objectives

By the end of this module, you will be able to:

- Write clean, modular SQL transformations in dbt
- Use Jinja templating to create dynamic SQL
- Implement macros for reusable SQL patterns
- Configure sources and use references properly
- Add tests to validate your data models

---

## 🧠 SQL Basics in dbt

### The dbt Approach to SQL

- **Modular SQL with CTEs**
- **One Model, One Purpose**
- **Consistent Naming Conventions**

---

## 📝 Modular SQL with CTEs

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customer_orders as (
    select
        c.customer_id,
        count(o.order_id) as order_count
    from customers c
    left join orders o on c.customer_id = o.customer_id
    group by 1
)

select * from customer_orders
```

---

## 🏗️ One Model, One Purpose

- **Staging models**: Clean and standardize raw data
  - Example: `stg_customers.sql`

- **Intermediate models**: Join and transform staging models
  - Example: `int_customer_orders.sql`

- **Mart models**: Create business-specific views
  - Example: `customer_overview.sql`

---

## 📋 Naming Conventions

- **Staging models**: `stg_[source]_[entity]`
  - Example: `stg_vyaparbazaar_customers`

- **Intermediate models**: `int_[entity]_[verb]`
  - Example: `int_orders_joined`

- **Mart models**: `[entity]_[purpose]`
  - Example: `customer_segmentation`

---

## 🧩 Jinja Templating

Jinja is a templating language that allows you to generate dynamic SQL.

```sql
{% set payment_methods = ['credit_card', 'debit_card', 'upi', 'cod'] %}

select
    order_id,
    {% for payment_method in payment_methods %}
    sum(case when payment_type = '{{ payment_method }}' then amount else 0 end) as {{ payment_method }}_amount,
    {% endfor %}
    sum(amount) as total_amount
from {{ ref('stg_payments') }}
group by 1
```

---

## 🔄 Jinja Control Structures

```sql
{% if target.name == 'dev' %}
    -- Limit data in development
    select * from {{ ref('stg_orders') }} limit 100
{% else %}
    -- Use all data in production
    select * from {{ ref('stg_orders') }}
{% endif %}
```

---

## 🧰 Macros: Reusable SQL Snippets

```sql
-- Define a macro
{% macro date_diff_in_days(start_date, end_date) %}
    datediff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

-- Use the macro in a model
select
    order_id,
    {{ date_diff_in_days('order_purchase_timestamp', 'order_delivered_customer_date') }} as delivery_time_days
from {{ ref('stg_orders') }}
```

---

## 📊 Practical Macro Examples

### Date Utilities

```sql
{% macro is_recent_date(date_column, days=30) %}
    {{ date_diff_in_days(date_column, 'current_date()') }} <= {{ days }}
{% endmacro %}

-- Usage
select * from customers where {{ is_recent_date('last_order_date', 60) }}
```

---

## 📊 Practical Macro Examples (cont.)

### String Utilities

```sql
{% macro categorize_email_domain(email_column) %}
    case
        when {{ extract_domain_from_email(email_column) }} like '%gmail.com%' then 'Gmail'
        when {{ extract_domain_from_email(email_column) }} like '%yahoo%' then 'Yahoo'
        else 'Other'
    end
{% endmacro %}
```

---

## 📦 Sources: Connecting to Raw Data

```yaml
# models/sources.yml
version: 2

sources:
  - name: vyaparbazaar_raw
    description: "Raw data from VyaparBazaar e-commerce platform"
    schema: main
    tables:
      - name: vyaparbazaar_customers
        description: "Customer information"
```

```sql
-- Using a source in a model
select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_customers') }}
```

---

## 🔗 References: Connecting to Other Models

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)
```

---

## 🧪 Testing Basics

### Why Test?

- Ensure data quality
- Catch issues early
- Document expectations
- Build confidence

---

## 🧪 Schema Tests

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_customers
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: customer_state
        tests:
          - accepted_values:
              values: ['SP', 'RJ', 'MG', 'RS', 'PR']
```

---

## 🧪 Relationship Tests

```yaml
models:
  - name: stg_orders
    columns:
      - name: customer_id
        tests:
          - relationships:
              to: ref('stg_customers')
              field: customer_id
```

---

## 🧪 Custom SQL Tests

```sql
-- tests/assert_positive_values.sql
{% test assert_positive_values(model, column_name) %}

with validation as (
    select
        {{ column_name }} as field_to_check
    from {{ model }}
),

validation_errors as (
    select
        field_to_check
    from validation
    where field_to_check <= 0 or field_to_check is null
)

select *
from validation_errors

{% endtest %}
```

---

## 🧪 Using Custom Tests

```yaml
models:
  - name: stg_order_items
    columns:
      - name: price
        tests:
          - assert_positive_values
```

---

## 🔄 Incremental Models

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id'
    )
}}

with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_orders') }}
    {% if is_incremental() %}
    where order_purchase_timestamp > (select max(order_purchase_timestamp) from {{ this }})
    {% endif %}
)

select * from source
```

---

## 🧪 Hands-on Exercises

### Exercise 2.1: Create a New Staging Model
- Create a staging model for support tickets
- Add appropriate tests

### Exercise 2.2: Use Jinja Templating for Dynamic SQL
- Create a model with dynamic SQL using Jinja

### Exercise 2.3: Create and Use a Custom Macro
- Create a macro for support ticket analysis

### Exercise 2.4: Add Tests to Your Models
- Add comprehensive tests to your models

### Exercise 2.5: Create a Mart Model
- Create a business-focused mart model

---

## 🚀 Real-world Impact

- **Reduced code duplication** with macros
- **Faster development** with templates
- **Fewer bugs** with testing
- **Better documentation** with schema files
- **Clearer data lineage** with sources and references

---

## 🎯 Key Takeaways

1. **Modular SQL** makes complex transformations manageable
2. **Jinja templating** enables dynamic SQL generation
3. **Macros** promote code reuse and standardization
4. **Sources and references** create clear data lineage
5. **Testing** ensures data quality and reliability

---

## 🔮 What's Next?

In **Module 3**, we'll dive deeper into:

- CTEs and modular SQL
- Intermediate models and aggregations
- Dimensional modeling concepts
- Performance considerations

---

## 🙋 Questions?

Let's discuss!

---

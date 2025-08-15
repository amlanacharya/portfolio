# Module 2: Data Transformation Fundamentals

Welcome to Module 2 of the VyaparBazaar Analytics Internship Camp! In this module, we'll dive deeper into the core concepts that make dbt a powerful tool for data transformation. You'll learn how to write effective SQL in dbt, leverage Jinja templating for dynamic SQL generation, understand sources and references, and implement testing to ensure data quality.

## 🎯 Learning Objectives

By the end of this module, you will be able to:
- Write clean, modular SQL transformations in dbt
- Use Jinja templating to create dynamic and reusable SQL
- Implement macros to standardize common SQL patterns
- Configure sources and use references properly
- Add tests to validate your data models

## 🧠 SQL Basics in dbt

### The dbt SQL Approach

dbt uses SQL as its primary language, but with a twist - it enhances SQL with templating capabilities. Let's look at the key principles of writing SQL in dbt:

#### 1. Modular SQL with CTEs

Common Table Expressions (CTEs) are a powerful way to organize your SQL code into logical blocks. In dbt, we use CTEs extensively to make our models more readable and maintainable:

```sql
-- Example of modular SQL with CTEs
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        count(o.order_id) as order_count,
        min(o.order_purchase_timestamp) as first_order_date,
        max(o.order_purchase_timestamp) as last_order_date
    from customers c
    left join orders o on c.customer_id = o.customer_id
    group by 1, 2, 3, 4
)

select * from customer_orders
```

#### 2. One Model, One Purpose

Each dbt model should have a single, clear purpose. This makes your models easier to understand, test, and maintain:

- **Staging models**: Clean and standardize raw data
- **Intermediate models**: Join and transform staging models
- **Mart models**: Create business-specific views for analysis

#### 3. Naming Conventions

Consistent naming helps everyone understand your models:

- **Staging models**: `stg_[source]_[entity]`
- **Intermediate models**: `int_[entity]_[verb]`
- **Mart models**: `[entity]_[purpose]`

## 🧩 Jinja Templating and Macros

### What is Jinja?

Jinja is a templating language that allows you to generate dynamic SQL. In dbt, Jinja is used to:

1. Reference other models
2. Use control structures (if/else, for loops)
3. Define and use macros (reusable SQL snippets)
4. Access dbt context variables

### Jinja Basics

#### Variables and Expressions

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

#### Control Structures

```sql
{% if target.name == 'dev' %}
    -- Limit data in development
    select * from {{ ref('stg_orders') }} limit 100
{% else %}
    -- Use all data in production
    select * from {{ ref('stg_orders') }}
{% endif %}
```

### Macros: Reusable SQL Snippets

Macros are like functions in other programming languages. They allow you to define reusable SQL snippets:

```sql
-- Define a macro
{% macro date_diff_in_days(start_date, end_date) %}
    datediff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

-- Use the macro in a model
select
    order_id,
    order_purchase_timestamp as purchase_date,
    order_delivered_customer_date as delivery_date,
    {{ date_diff_in_days('order_purchase_timestamp', 'order_delivered_customer_date') }} as delivery_time_days
from {{ ref('stg_orders') }}
where order_delivered_customer_date is not null
```

### Practical Macro Examples

Let's look at some practical macros from our project:

#### Date Utilities

```sql
{% macro is_recent_date(date_column, days=30) %}
    {{ date_diff_in_days(date_column, 'current_date()') }} <= {{ days }}
{% endmacro %}

-- Usage
select
    customer_id,
    last_order_date
from {{ ref('int_customer_orders') }}
where {{ is_recent_date('last_order_date', 60) }}
```

#### String Utilities

```sql
{% macro categorize_email_domain(email_column) %}
    case
        when {{ extract_domain_from_email(email_column) }} like '%gmail.com%' then 'Gmail'
        when {{ extract_domain_from_email(email_column) }} like '%yahoo%' then 'Yahoo'
        when {{ extract_domain_from_email(email_column) }} like '%hotmail%' then 'Hotmail'
        when {{ extract_domain_from_email(email_column) }} like '%outlook%' then 'Outlook'
        when {{ extract_domain_from_email(email_column) }} like '%.edu%' then 'Education'
        when {{ extract_domain_from_email(email_column) }} like '%.gov%' then 'Government'
        when {{ extract_domain_from_email(email_column) }} like '%.org%' then 'Organization'
        else 'Other'
    end
{% endmacro %}
```

## 📊 Sources and References

### Sources: Connecting to Raw Data

Sources define the raw data tables in your database. They are configured in YAML files:

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
        columns:
          - name: customer_id
            description: "Unique identifier for a customer"
```

To use a source in a model:

```sql
select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_customers') }}
```

### References: Connecting to Other Models

References allow models to depend on other models:

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)
```

### Benefits of Sources and References

1. **Dependency Tracking**: dbt automatically builds a dependency graph
2. **Documentation**: Sources and references are documented in dbt docs
3. **Testing**: You can add tests to sources and referenced models
4. **Compilation**: dbt ensures models are built in the correct order

## 🧪 Testing Basics

### Why Test?

Testing ensures your data models are reliable and meet your expectations. dbt supports two types of tests:

1. **Schema tests**: Defined in YAML files
2. **Custom SQL tests**: SQL queries that return failing records

### Schema Tests

Schema tests are defined in YAML files and applied to models:

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
              values: ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'ES', 'PE', 'CE']
```

### Relationship Tests

Relationship tests ensure referential integrity between models:

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

### Custom SQL Tests

Custom SQL tests are SQL queries that return failing records:

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

To use a custom test:

```yaml
models:
  - name: stg_order_items
    columns:
      - name: price
        tests:
          - assert_positive_values
```

## 🧪 Hands-on Exercises

Now that you understand the fundamentals, let's apply them with some hands-on exercises. See the [Module 2 Exercises](module2_exercises.md) document for detailed instructions.

## 📚 Additional Resources

- [dbt Jinja Documentation](https://docs.getdbt.com/docs/building-a-dbt-project/jinja-macros)
- [dbt Testing Documentation](https://docs.getdbt.com/docs/building-a-dbt-project/tests)
- [dbt Sources Documentation](https://docs.getdbt.com/docs/building-a-dbt-project/using-sources)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)

## 🎯 Next Steps

In Module 3, we'll dive deeper into advanced data modeling techniques, including CTEs, intermediate models, dimensional modeling concepts, and performance considerations.

Happy modeling!

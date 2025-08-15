# Module 2: Data Transformation Fundamentals - Exercise Solutions

This document provides detailed solutions for the exercises in Module 2 of the VyaparBazaar Analytics Internship Camp.

## Exercise 2.1: Create a New Staging Model

### Solution

1. First, we examine the `sources.yml` file to understand the structure of the `vyaparbazaar_support_tickets` source.

2. Create a new file `stg_support_tickets.sql` in the `models/staging/` directory:

```sql
with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_support_tickets') }}
),

renamed as (
    select
        ticket_id,
        customer_id,
        order_id,
        cast(created_at as timestamp) as created_at,
        category,
        channel,
        status,
        cast(resolved_at as timestamp) as resolved_at,
        satisfaction_rating,
        priority
    from source
)

select * from renamed
```

3. Run the model:
```bash
dbt run -m stg_support_tickets
```

4. Add the model to `models/staging/schema.yml`:

```yaml
  - name: stg_support_tickets
    description: "Cleaned and standardized support ticket data from the raw source"
    columns:
      - name: ticket_id
        description: "Unique identifier for the support ticket"
        tests:
          - unique
          - not_null
      - name: customer_id
        description: "Customer identifier"
        tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: customer_id
      - name: order_id
        description: "Related order if applicable"
        tests:
          - relationships:
              to: ref('stg_orders')
              field: order_id
      - name: created_at
        description: "Ticket creation timestamp"
        tests:
          - not_null
      - name: category
        description: "Support ticket category"
        tests:
          - not_null
      - name: channel
        description: "Support channel"
      - name: status
        description: "Ticket status"
        tests:
          - accepted_values:
              values: ['open', 'in_progress', 'resolved', 'closed', 'cancelled']
      - name: resolved_at
        description: "Resolution timestamp"
      - name: satisfaction_rating
        description: "Customer satisfaction rating (1-5)"
      - name: priority
        description: "Ticket priority"
        tests:
          - accepted_values:
              values: ['low', 'medium', 'high', 'urgent']
```

### Key Points

- We cast date/timestamp columns to the appropriate types
- We follow the naming convention `stg_[source]_[entity]`
- We add appropriate tests for each column
- We ensure referential integrity with relationships tests

## Exercise 2.2: Use Jinja Templating for Dynamic SQL

### Solution

1. Create a new file `int_support_ticket_summary.sql` in the `models/intermediate/` directory:

```sql
{% set status_values = ['open', 'in_progress', 'resolved', 'closed', 'cancelled'] %}

with support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

ticket_summary as (
    select
        category,
        count(*) as total_tickets,
        {% for status in status_values %}
        sum(case when status = '{{ status }}' then 1 else 0 end) as {{ status }}_tickets,
        {% endfor %}
        avg(case when resolved_at is not null 
            then datediff('hour', created_at, resolved_at) 
            else null end) as avg_resolution_time_hours
    from support_tickets
    group by 1
)

select * from ticket_summary
```

2. Run the model:
```bash
dbt run -m int_support_ticket_summary
```

3. Add the model to `models/intermediate/schema.yml`:

```yaml
  - name: int_support_ticket_summary
    description: "Summary of support tickets by category and status"
    columns:
      - name: category
        description: "Support ticket category"
        tests:
          - not_null
          - unique
      - name: total_tickets
        description: "Total number of tickets in this category"
        tests:
          - not_null
      - name: open_tickets
        description: "Number of open tickets in this category"
      - name: in_progress_tickets
        description: "Number of in-progress tickets in this category"
      - name: resolved_tickets
        description: "Number of resolved tickets in this category"
      - name: closed_tickets
        description: "Number of closed tickets in this category"
      - name: cancelled_tickets
        description: "Number of cancelled tickets in this category"
      - name: avg_resolution_time_hours
        description: "Average resolution time in hours"
```

### Key Points

- We use Jinja's `{% set %}` to define a list of status values
- We use Jinja's `{% for %}` loop to generate dynamic SQL for each status
- We handle null values in the resolution time calculation
- This approach makes the SQL more maintainable and adaptable to changes

## Exercise 2.3: Create and Use a Custom Macro

### Solution

1. Create a new file `support_utils.sql` in the `macros/` directory:

```sql
{% macro calculate_resolution_time(created_at, resolved_at, unit='hour') %}
    case
        when {{ resolved_at }} is null then null
        when {{ unit }} = 'minute' then datediff('minute', {{ created_at }}, {{ resolved_at }})
        when {{ unit }} = 'hour' then datediff('hour', {{ created_at }}, {{ resolved_at }})
        when {{ unit }} = 'day' then datediff('day', {{ created_at }}, {{ resolved_at }})
        else datediff('hour', {{ created_at }}, {{ resolved_at }})
    end
{% endmacro %}

{% macro categorize_resolution_time(resolution_time_hours) %}
    case
        when {{ resolution_time_hours }} is null then 'Unresolved'
        when {{ resolution_time_hours }} <= 1 then 'Under 1 hour'
        when {{ resolution_time_hours }} <= 4 then '1-4 hours'
        when {{ resolution_time_hours }} <= 24 then '4-24 hours'
        when {{ resolution_time_hours }} <= 72 then '1-3 days'
        else 'Over 3 days'
    end
{% endmacro %}
```

2. Create a new file `int_customer_support_performance.sql` in the `models/intermediate/` directory:

```sql
with support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

ticket_metrics as (
    select
        ticket_id,
        customer_id,
        category,
        created_at,
        resolved_at,
        {{ calculate_resolution_time('created_at', 'resolved_at', 'hour') }} as resolution_time_hours,
        satisfaction_rating
    from support_tickets
),

ticket_categories as (
    select
        ticket_id,
        customer_id,
        category,
        resolution_time_hours,
        {{ categorize_resolution_time('resolution_time_hours') }} as resolution_time_category,
        satisfaction_rating
    from ticket_metrics
)

select * from ticket_categories
```

3. Run the model:
```bash
dbt run -m int_customer_support_performance
```

4. Add the model to `models/intermediate/schema.yml`:

```yaml
  - name: int_customer_support_performance
    description: "Support ticket performance metrics"
    columns:
      - name: ticket_id
        description: "Unique identifier for the support ticket"
        tests:
          - unique
          - not_null
      - name: customer_id
        description: "Customer identifier"
        tests:
          - not_null
      - name: category
        description: "Support ticket category"
      - name: resolution_time_hours
        description: "Resolution time in hours"
      - name: resolution_time_category
        description: "Categorized resolution time"
      - name: satisfaction_rating
        description: "Customer satisfaction rating (1-5)"
```

### Key Points

- We create reusable macros for common calculations
- The macros accept parameters for flexibility
- We use the macros in our model to standardize calculations
- This approach ensures consistency across models and reduces code duplication

## Exercise 2.4: Add Tests to Your Models

### Solution

1. Update the `models/intermediate/schema.yml` file to add tests to the new intermediate models (already shown in previous solutions).

2. Create a new custom test `assert_valid_satisfaction_rating.sql` in the `tests/` directory:

```sql
{% test assert_valid_satisfaction_rating(model, column_name) %}

with validation as (
    select
        {{ column_name }} as rating
    from {{ model }}
),

validation_errors as (
    select
        rating
    from validation
    where rating is not null and (rating < 1 or rating > 5)
)

select *
from validation_errors

{% endtest %}
```

3. Apply this test to the `satisfaction_rating` column in the `int_customer_support_performance` model:

```yaml
  - name: int_customer_support_performance
    description: "Support ticket performance metrics"
    columns:
      # ... other columns
      - name: satisfaction_rating
        description: "Customer satisfaction rating (1-5)"
        tests:
          - assert_valid_satisfaction_rating
```

4. Run all tests:
```bash
dbt test
```

### Key Points

- We create a custom test for validating satisfaction ratings
- We apply the test to the appropriate column
- Custom tests follow the same pattern as built-in tests
- Tests help ensure data quality and catch issues early

## Exercise 2.5: Create a Mart Model Using Sources and References

### Solution

1. Create a new file `customer_support_mart.sql` in the `models/marts/` directory:

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('int_orders_with_items') }}
),

support_performance as (
    select * from {{ ref('int_customer_support_performance') }}
),

customer_orders as (
    select
        customer_id,
        count(distinct order_id) as order_count,
        sum(payment_value) as total_spend
    from orders
    group by 1
),

customer_support as (
    select
        customer_id,
        count(*) as ticket_count,
        avg(resolution_time_hours) as avg_resolution_time,
        avg(satisfaction_rating) as avg_satisfaction
    from support_performance
    group by 1
),

final as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        coalesce(co.order_count, 0) as order_count,
        coalesce(co.total_spend, 0) as total_spend,
        coalesce(cs.ticket_count, 0) as ticket_count,
        cs.avg_resolution_time,
        cs.avg_satisfaction,
        case
            when cs.ticket_count = 0 then 'No Support Interaction'
            when cs.avg_satisfaction >= 4 then 'Highly Satisfied'
            when cs.avg_satisfaction >= 3 then 'Satisfied'
            when cs.avg_satisfaction < 3 then 'Dissatisfied'
            else 'Unknown'
        end as satisfaction_segment
    from customers c
    left join customer_orders co on c.customer_id = co.customer_id
    left join customer_support cs on c.customer_id = cs.customer_id
)

select * from final
```

2. Run the model:
```bash
dbt run -m customer_support_mart
```

3. Add the model to `models/marts/schema.yml`:

```yaml
  - name: customer_support_mart
    description: "Business-focused customer support overview for analytics and reporting"
    columns:
      - name: customer_id
        description: "Unique identifier for a customer"
        tests:
          - unique
          - not_null
      - name: customer_unique_id
        description: "Unique identifier that represents a customer across the platform"
      - name: customer_city
        description: "Customer city name"
      - name: customer_state
        description: "Customer state"
      - name: order_count
        description: "Total number of orders placed by the customer"
        tests:
          - not_null
      - name: total_spend
        description: "Total amount spent by the customer"
        tests:
          - not_null
      - name: ticket_count
        description: "Total number of support tickets created by the customer"
        tests:
          - not_null
      - name: avg_resolution_time
        description: "Average resolution time for customer's support tickets in hours"
      - name: avg_satisfaction
        description: "Average satisfaction rating for customer's support tickets"
      - name: satisfaction_segment
        description: "Customer segment based on support satisfaction"
        tests:
          - accepted_values:
              values: ['No Support Interaction', 'Highly Satisfied', 'Satisfied', 'Dissatisfied', 'Unknown']
```

### Key Points

- We use references to build on existing models
- We create a business-focused mart model that combines multiple data sources
- We add derived fields that provide business insights
- We document the model thoroughly for business users

## Bonus Challenge: Create an Incremental Model

### Solution

1. Modify the `stg_support_tickets.sql` model to use incremental materialization:

```sql
{{
    config(
        materialized='incremental',
        unique_key='ticket_id'
    )
}}

with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_support_tickets') }}
    {% if is_incremental() %}
    where created_at > (select max(created_at) from {{ this }})
    {% endif %}
),

renamed as (
    select
        ticket_id,
        customer_id,
        order_id,
        cast(created_at as timestamp) as created_at,
        category,
        channel,
        status,
        cast(resolved_at as timestamp) as resolved_at,
        satisfaction_rating,
        priority
    from source
)

select * from renamed
```

2. Run the incremental model:
```bash
dbt run -m stg_support_tickets
```

### Benefits and Trade-offs of Incremental Materialization

**Benefits:**
1. **Faster Builds**: Only processes new or changed data
2. **Resource Efficiency**: Reduces computational resources needed
3. **Reduced Downtime**: Less time spent rebuilding large tables
4. **Scalability**: Works well with growing datasets

**Trade-offs:**
1. **Complexity**: More complex than full-refresh models
2. **Maintenance**: Requires careful management of the incremental logic
3. **Data Consistency**: May miss updates to historical data
4. **Testing Challenges**: More difficult to test thoroughly

**When to Use Incremental Models:**
- Large tables that are frequently updated
- Tables where historical data rarely changes
- Performance-critical models
- When build time is a concern

**When to Avoid Incremental Models:**
- Small tables where full refresh is fast
- When historical data frequently changes
- When the incremental logic would be too complex
- During initial development and testing phases

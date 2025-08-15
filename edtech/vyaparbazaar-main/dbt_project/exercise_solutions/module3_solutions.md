# Module 3: Advanced Data Modeling Techniques - Exercise Solutions

This document provides detailed solutions for the exercises in Module 3 of the VyaparBazaar Analytics Internship Camp.

## Exercise 3.1: Create a Date Dimension Model

### Solution

1. First, we create the dimensions directory if it doesn't exist:
```bash
mkdir -p models/dimensions
```

2. Create the `dim_date.sql` file in the `models/dimensions/` directory:

```sql
-- models/dimensions/dim_date.sql
{{ config(materialized='table') }}

{% set start_date = "cast('2016-01-01' as date)" %}
{% set end_date = "cast('2023-12-31' as date)" %}

with date_spine as (
    {{ dbt_utils.date_spine(
        start_date=start_date,
        end_date=end_date,
        datepart="day"
    ) }}
),

dates as (
    select
        -- Date key in YYYYMMDD format
        cast(date_format(date_day, '%Y%m%d') as int) as date_key,
        date_day as calendar_date,

        -- Standard date parts
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(quarter from date_day) as quarter,
        extract(dayofweek from date_day) as day_of_week,
        extract(dayofyear from date_day) as day_of_year,

        -- Weekend indicator
        case
            when extract(dayofweek from date_day) in (0, 6) then true
            else false
        end as is_weekend,

        -- Holiday indicator (simplified for this exercise)
        case
            when (extract(month from date_day) = 1 and extract(day from date_day) = 26) then true  -- Republic Day
            when (extract(month from date_day) = 8 and extract(day from date_day) = 15) then true  -- Independence Day
            when (extract(month from date_day) = 10 and extract(day from date_day) = 2) then true  -- Gandhi Jayanti
            else false
        end as is_holiday,

        -- Festival season indicator
        case
            when extract(month from date_day) between 9 and 11 then true
            else false
        end as is_festival_season,

        -- Fiscal year (April-March)
        case
            when extract(month from date_day) >= 4 then extract(year from date_day)
            else extract(year from date_day) - 1
        end as fiscal_year,

        -- Fiscal quarter
        case
            when extract(month from date_day) between 4 and 6 then 1
            when extract(month from date_day) between 7 and 9 then 2
            when extract(month from date_day) between 10 and 12 then 3
            else 4
        end as fiscal_quarter,

        -- Season
        case
            when extract(month from date_day) between 3 and 5 then 'Spring'
            when extract(month from date_day) between 6 and 8 then 'Summer'
            when extract(month from date_day) = 9 then 'Monsoon'
            when extract(month from date_day) between 10 and 11 then 'Autumn'
            else 'Winter'
        end as season
    from date_spine
)

select * from dates
```

3. Create the schema.yml file in the dimensions directory:

```yaml
# models/dimensions/schema.yml
version: 2

models:
  - name: dim_date
    description: "Date dimension table for time-based analysis"
    columns:
      - name: date_key
        description: "Primary key in YYYYMMDD format"
        tests:
          - unique
          - not_null
      - name: calendar_date
        description: "Actual date"
        tests:
          - not_null
      - name: year
        description: "Calendar year"
      - name: month
        description: "Calendar month (1-12)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 12
      - name: day
        description: "Day of month (1-31)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 31
      - name: quarter
        description: "Calendar quarter (1-4)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 4
      - name: day_of_week
        description: "Day of week (0=Sunday, 6=Saturday)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 6
      - name: day_of_year
        description: "Day of year (1-366)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 366
      - name: is_weekend
        description: "Flag indicating if date is a weekend"
      - name: is_holiday
        description: "Flag indicating if date is an Indian holiday"
      - name: is_festival_season
        description: "Flag indicating if date is during festival season (Sep-Nov)"
      - name: fiscal_year
        description: "Fiscal year (April-March)"
      - name: fiscal_quarter
        description: "Fiscal quarter (1-4, starting in April)"
        tests:
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 4
      - name: season
        description: "Season (Spring, Summer, Monsoon, Autumn, Winter)"
        tests:
          - accepted_values:
              values: ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']
```

### Key Points

- We use the `dbt_utils.date_spine` macro to generate a continuous series of dates
- We derive various date attributes using SQL functions
- We implement fiscal year and quarter calculations specific to the Indian fiscal calendar
- We add comprehensive tests to ensure data quality
- The model is materialized as a table for optimal query performance

## Exercise 3.2: Build an Order Facts Model

### Solution

1. First, we create the facts directory if it doesn't exist:
```bash
mkdir -p models/facts
```

2. Create the `fct_orders.sql` file in the `models/facts/` directory:

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

-- Aggregate payments by order
order_payments as (
    select
        order_id,
        sum(payment_value) as order_total,
        array_agg(payment_type) as payment_methods
    from payments
    group by 1
),

-- Aggregate order items by order
order_items_agg as (
    select
        order_id,
        count(*) as item_count,
        sum(price) as items_price,
        sum(freight_value) as freight_value
    from order_items
    group by 1
),

-- Join everything together
order_facts as (
    select
        o.order_id,
        o.customer_id,
        cast(date_format(o.order_purchase_timestamp, '%Y%m%d') as int) as order_date_key,
        o.order_purchase_timestamp as order_date,
        o.order_status,
        op.order_total,
        op.payment_methods,
        oi.item_count,
        oi.items_price,
        oi.freight_value,
        {{ datediff('o.order_purchase_timestamp', 'o.order_delivered_customer_date', 'day') }} as delivery_time_days,
        case
            when o.order_delivered_customer_date > o.order_estimated_delivery_date then true
            else false
        end as is_delayed
    from orders o
    left join order_payments op on o.order_id = op.order_id
    left join order_items_agg oi on o.order_id = oi.order_id
)

select * from order_facts
```

3. Create the schema.yml file in the facts directory:

```yaml
# models/facts/schema.yml
version: 2

models:
  - name: fct_orders
    description: "Fact table for order analysis"
    columns:
      - name: order_id
        description: "Primary key - unique identifier for the order"
        tests:
          - unique
          - not_null
      - name: customer_id
        description: "Foreign key to dim_customers"
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: order_date_key
        description: "Foreign key to dim_date"
        tests:
          - not_null
          - relationships:
              to: ref('dim_date')
              field: date_key
      - name: order_date
        description: "Timestamp when the order was placed"
        tests:
          - not_null
      - name: order_status
        description: "Current status of the order"
        tests:
          - not_null
          - accepted_values:
              values: ['delivered', 'shipped', 'processing', 'canceled', 'unavailable']
      - name: order_total
        description: "Total amount paid for the order"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10000
      - name: payment_methods
        description: "Array of payment methods used for the order"
      - name: item_count
        description: "Number of items in the order"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 1
              max_value: 100
      - name: items_price
        description: "Sum of item prices before freight"
        tests:
          - not_null
      - name: freight_value
        description: "Total freight value for the order"
        tests:
          - not_null
      - name: delivery_time_days
        description: "Number of days between order and delivery"
      - name: is_delayed
        description: "Flag indicating if the order was delivered after the estimated date"
    tests:
      - dbt_utils.expression_is_true:
          expression: "abs(order_total - (items_price + freight_value)) < 0.01"
          where: "order_status != 'canceled'"
```

### Key Points

- We join multiple staging models to create a comprehensive fact table
- We use CTEs to organize the logic and make the SQL more readable
- We create derived metrics like delivery time and delay status
- We implement comprehensive tests, including a custom test to ensure order_total equals items_price plus freight_value
- We use the date dimension as a foreign key for time-based analysis

## Exercise 3.3: Create an Incremental Clickstream Model

### Solution

1. Create the `int_clickstream_events.sql` file in the `models/intermediate/` directory:

```sql
-- models/intermediate/int_clickstream_events.sql
{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

with source as (
    select * from {{ ref('stg_clickstream') }}
    {% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
    {% endif %}
),

transformed as (
    select
        event_id,
        customer_id,
        cast(date_format(event_timestamp, '%Y%m%d') as int) as event_date_key,
        event_timestamp,
        event_type,
        page_type,
        -- Derive device category
        case
            when lower(device) like '%mobile%' or lower(device) like '%phone%' then 'Mobile'
            when lower(device) like '%tablet%' or lower(device) like '%ipad%' then 'Tablet'
            else 'Desktop'
        end as device_category,
        -- Derive browser category
        case
            when lower(browser) like '%chrome%' then 'Chrome'
            when lower(browser) like '%firefox%' then 'Firefox'
            when lower(browser) like '%safari%' then 'Safari'
            when lower(browser) like '%edge%' then 'Edge'
            when lower(browser) like '%opera%' then 'Opera'
            else 'Other'
        end as browser_category,
        session_id,
        -- Event type flags
        case when lower(event_type) like '%purchase%' then true else false end as is_purchase_event,
        case when lower(event_type) like '%cart%' then true else false end as is_cart_event,
        case when lower(event_type) like '%product%' and lower(event_type) like '%view%' then true else false end as is_product_view_event
    from source
)

select * from transformed
```

2. Update the schema.yml file in the intermediate directory:

```yaml
# models/intermediate/schema.yml
version: 2

models:
  - name: int_clickstream_events
    description: "Intermediate model for clickstream events with derived attributes"
    config:
      tags: ['incremental', 'clickstream']
    columns:
      - name: event_id
        description: "Primary key - unique identifier for the event"
        tests:
          - unique
          - not_null
      - name: customer_id
        description: "Foreign key to dim_customers"
        tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
              severity: warn
      - name: event_date_key
        description: "Foreign key to dim_date"
        tests:
          - relationships:
              to: ref('dim_date')
              field: date_key
      - name: event_timestamp
        description: "Timestamp when the event occurred"
        tests:
          - not_null
      - name: event_type
        description: "Type of event"
      - name: page_type
        description: "Type of page where the event occurred"
      - name: device_category
        description: "Categorized device type (Mobile, Tablet, Desktop)"
        tests:
          - accepted_values:
              values: ['Mobile', 'Tablet', 'Desktop']
      - name: browser_category
        description: "Categorized browser (Chrome, Firefox, Safari, Edge, Opera, Other)"
        tests:
          - accepted_values:
              values: ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera', 'Other']
      - name: session_id
        description: "Session identifier"
      - name: is_purchase_event
        description: "Flag indicating if this is a purchase event"
      - name: is_cart_event
        description: "Flag indicating if this is a cart-related event"
      - name: is_product_view_event
        description: "Flag indicating if this is a product view event"
```

### Key Points

- We use incremental materialization to efficiently process only new data
- We include logic to filter for new records since the last run
- We derive useful categorizations from the raw data
- We create boolean flags for common event types to simplify downstream analysis
- We use foreign keys to connect to dimension tables
- We set some tests to warning severity for customer_id since not all events may have an associated customer

## Exercise 3.4: Build a Customer Behavior Mart Model

### Solution

1. First, we create the customer_marts directory if it doesn't exist:
```bash
mkdir -p models/marts/customer_marts
```

2. Create the `customer_behavior.sql` file:

```sql
-- models/marts/customer_marts/customer_behavior.sql
{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('dim_customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

clickstream as (
    select * from {{ ref('int_clickstream_events') }}
),

-- Calculate order metrics per customer
customer_orders as (
    select
        customer_id,
        count(order_id) as order_count,
        sum(order_total) as total_spend,
        avg(order_total) as avg_order_value,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        {{ datediff('min(order_date)', 'max(order_date)', 'day') }} as customer_lifetime_days,
        {{ datediff('max(order_date)', 'current_timestamp()', 'day') }} as days_since_last_order
    from orders
    group by 1
),

-- Calculate days between orders using window functions
order_intervals as (
    select
        customer_id,
        order_id,
        order_date,
        lag(order_date) over (partition by customer_id order by order_date) as prev_order_date,
        {{ datediff('lag(order_date) over (partition by customer_id order by order_date)', 'order_date', 'day') }} as days_between_orders
    from orders
),

-- Average days between orders
customer_purchase_frequency as (
    select
        customer_id,
        avg(days_between_orders) as avg_days_between_orders
    from order_intervals
    where days_between_orders is not null
    group by 1
),

-- Clickstream metrics
customer_clickstream as (
    select
        customer_id,
        count(*) as total_events,
        count(distinct session_id) as total_sessions,
        sum(case when is_product_view_event then 1 else 0 end) as product_view_count,
        sum(case when is_cart_event then 1 else 0 end) as cart_event_count,
        sum(case when is_purchase_event then 1 else 0 end) as purchase_event_count,
        count(distinct device_category) as device_count,
        -- Most used device
        first_value(device_category) over (
            partition by customer_id
            order by count(*) desc
            rows between unbounded preceding and unbounded following
        ) as preferred_device
    from clickstream
    group by customer_id
),

-- Calculate conversion rates
customer_conversion as (
    select
        customer_id,
        total_events,
        total_sessions,
        product_view_count,
        cart_event_count,
        purchase_event_count,
        device_count,
        preferred_device,
        case
            when product_view_count > 0 then
                round(cast(purchase_event_count as float) / cast(product_view_count as float), 3)
            else 0
        end as browse_to_purchase_rate
    from customer_clickstream
),

-- Final customer behavior model
customer_behavior as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,

        -- Order metrics
        coalesce(co.order_count, 0) as order_count,
        coalesce(co.total_spend, 0) as total_spend,
        coalesce(co.avg_order_value, 0) as avg_order_value,
        co.first_order_date,
        co.last_order_date,
        coalesce(co.customer_lifetime_days, 0) as customer_lifetime_days,
        coalesce(co.days_since_last_order, 999) as days_since_last_order,
        coalesce(cpf.avg_days_between_orders, 0) as avg_days_between_orders,

        -- Clickstream metrics
        coalesce(cc.total_events, 0) as total_events,
        coalesce(cc.total_sessions, 0) as total_sessions,
        coalesce(cc.product_view_count, 0) as product_view_count,
        coalesce(cc.cart_event_count, 0) as cart_event_count,
        coalesce(cc.purchase_event_count, 0) as purchase_event_count,
        coalesce(cc.browse_to_purchase_rate, 0) as browse_to_purchase_rate,
        cc.preferred_device,

        -- RFM Segmentation
        case
            when co.days_since_last_order <= 30 then 'Recent'
            when co.days_since_last_order <= 90 then 'Moderate'
            else 'Lapsed'
        end as recency_segment,

        case
            when co.order_count >= 4 then 'High'
            when co.order_count >= 2 then 'Medium'
            when co.order_count = 1 then 'Low'
            else 'None'
        end as frequency_segment,

        case
            when co.total_spend >= 1000 then 'High'
            when co.total_spend >= 500 then 'Medium'
            when co.total_spend > 0 then 'Low'
            else 'None'
        end as monetary_segment,

        -- Combined RFM segment
        case
            when co.days_since_last_order <= 30 and co.order_count >= 4 and co.total_spend >= 1000 then 'Champions'
            when co.days_since_last_order <= 30 and co.order_count >= 2 then 'Loyal Customers'
            when co.days_since_last_order <= 90 and co.order_count >= 2 then 'Potential Loyalists'
            when co.days_since_last_order > 90 and co.order_count >= 4 and co.total_spend >= 1000 then 'At Risk'
            when co.days_since_last_order > 90 and co.order_count >= 2 then 'Needs Attention'
            when co.order_count = 1 then 'New Customers'
            when co.order_count = 0 and cc.total_events > 0 then 'Prospects'
            else 'Inactive'
        end as customer_segment

    from customers c
    left join customer_orders co on c.customer_id = co.customer_id
    left join customer_purchase_frequency cpf on c.customer_id = cpf.customer_id
    left join customer_conversion cc on c.customer_id = cc.customer_id
)

select * from customer_behavior
```

3. Create the schema.yml file in the customer_marts directory:

```yaml
# models/marts/customer_marts/schema.yml
version: 2

models:
  - name: customer_behavior
    description: "Customer behavior analysis with RFM segmentation and clickstream insights"
    columns:
      - name: customer_id
        description: "Primary key - unique identifier for the customer"
        tests:
          - unique
          - not_null
      - name: customer_unique_id
        description: "Unique identifier that represents a customer across the platform"
      - name: customer_city
        description: "Customer city name"
      - name: customer_state
        description: "Customer state"

      # Order metrics
      - name: order_count
        description: "Number of orders placed by the customer"
      - name: total_spend
        description: "Total amount spent by the customer"
      - name: avg_order_value
        description: "Average order value for the customer"
      - name: first_order_date
        description: "Date of the customer's first order"
      - name: last_order_date
        description: "Date of the customer's most recent order"
      - name: customer_lifetime_days
        description: "Number of days between first and last order"
      - name: days_since_last_order
        description: "Number of days since the customer's last order"
      - name: avg_days_between_orders
        description: "Average number of days between orders"

      # Clickstream metrics
      - name: total_events
        description: "Total number of clickstream events for the customer"
      - name: total_sessions
        description: "Total number of sessions for the customer"
      - name: product_view_count
        description: "Number of product view events"
      - name: cart_event_count
        description: "Number of cart-related events"
      - name: purchase_event_count
        description: "Number of purchase events"
      - name: browse_to_purchase_rate
        description: "Ratio of purchases to product views"
      - name: preferred_device
        description: "Customer's most frequently used device"

      # Segmentation
      - name: recency_segment
        description: "Segment based on recency of last order"
        tests:
          - accepted_values:
              values: ['Recent', 'Moderate', 'Lapsed']
      - name: frequency_segment
        description: "Segment based on order frequency"
        tests:
          - accepted_values:
              values: ['High', 'Medium', 'Low', 'None']
      - name: monetary_segment
        description: "Segment based on total spend"
        tests:
          - accepted_values:
              values: ['High', 'Medium', 'Low', 'None']
      - name: customer_segment
        description: "Combined RFM customer segment"
        tests:
          - accepted_values:
              values: ['Champions', 'Loyal Customers', 'Potential Loyalists', 'At Risk', 'Needs Attention', 'New Customers', 'Prospects', 'Inactive']
```

### Key Points

- We join dimension and fact tables to create a comprehensive customer view
- We use window functions to calculate metrics like days between orders
- We implement RFM segmentation to categorize customers
- We combine order data with clickstream data for a holistic view
- We use coalesce to handle null values for customers with no orders or events
- We create a customer_segment field that combines multiple factors for easy analysis

## Exercise 3.5: Implement Advanced Testing

### Solution

1. First, we create the generic tests directory:
```bash
mkdir -p tests/generic
```

2. Create the `test_values_in_range.sql` file:

```sql
-- tests/generic/test_values_in_range.sql
{% test values_in_range(model, column_name, min_value, max_value) %}

select
    *
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}

{% endtest %}
```

3. Create the `test_values_increasing.sql` file:

```sql
-- tests/generic/test_values_increasing.sql
{% test values_increasing(model, column_name, partition_by, order_by) %}

with windowed as (
    select
        {{ column_name }},
        lag({{ column_name }}) over (
            partition by {{ partition_by }}
            order by {{ order_by }}
        ) as prev_value
    from {{ model }}
)

select
    *
from windowed
where {{ column_name }} < prev_value
  and prev_value is not null

{% endtest %}
```

4. Create a singular test directory and add a test:
```bash
mkdir -p tests/singular
```

```sql
-- tests/singular/test_total_sales_match.sql
-- Test that total sales in fct_orders matches the total in the source data

with source_total as (
    select sum(payment_value) as total_sales
    from {{ ref('stg_payments') }}
),

fact_total as (
    select sum(order_total) as total_sales
    from {{ ref('fct_orders') }}
)

select
    'Total sales mismatch' as failure_reason,
    s.total_sales as source_total,
    f.total_sales as fact_total,
    abs(s.total_sales - f.total_sales) as difference
from source_total s
cross join fact_total f
where abs(s.total_sales - f.total_sales) > 0.01
```

5. Update the schema.yml files to use the new tests:

```yaml
# models/facts/schema.yml (partial update)
version: 2

models:
  - name: fct_orders
    # ... existing configuration ...
    columns:
      - name: order_total
        tests:
          - values_in_range:
              min_value: 0
              max_value: 10000
      # ... other columns ...
```

```yaml
# models/marts/customer_marts/schema.yml (partial update)
version: 2

models:
  - name: customer_behavior
    # ... existing configuration ...
    columns:
      - name: total_spend
        tests:
          - values_in_range:
              min_value: 0
              max_value: 100000
      - name: avg_order_value
        tests:
          - values_in_range:
              min_value: 0
              max_value: 10000
      # ... other columns ...
```

6. Install and use dbt-expectations:

Add to packages.yml:
```yaml
packages:
  - package: calogica/dbt_expectations
    version: 0.8.0
```

Run `dbt deps` to install the package.

Update schema.yml files to use dbt-expectations tests:

```yaml
# models/dimensions/schema.yml (partial update)
version: 2

models:
  - name: dim_date
    # ... existing configuration ...
    columns:
      - name: calendar_date
        tests:
          - dbt_expectations.expect_row_values_to_have_recent_data:
              datepart: year
              interval: 1
      - name: month
        tests:
          - dbt_expectations.expect_column_values_to_be_in_type_list:
              value_type: ["integer"]
      # ... other columns ...
```

```yaml
# models/intermediate/schema.yml (partial update)
version: 2

models:
  - name: int_clickstream_events
    # ... existing configuration ...
    columns:
      - name: event_timestamp
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: "'2016-01-01'"
              max_value: "current_timestamp()"
      # ... other columns ...
    tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1
          max_value: 1000000000
```

### Key Points

- We create custom generic tests that can be reused across models
- We implement a singular test to validate a specific business rule
- We use dbt-expectations for advanced testing capabilities
- We apply tests to appropriate columns based on their data characteristics
- We use different severity levels for tests based on their importance

## Bonus Challenge: Create a Product Performance Analysis Model

### Solution

1. First, we create the product_marts directory:
```bash
mkdir -p models/marts/product_marts
```

2. Create the `product_performance.sql` file:

```sql
-- models/marts/product_marts/product_performance.sql
{% set analysis_period = var('analysis_period', 'all') %}
{% set product_categories = var('product_categories', 'all') %}

{{ config(materialized='table') }}

with products as (
    select * from {{ ref('stg_products') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
    {% if analysis_period != 'all' %}
    where {{ get_date_filter('order_date', analysis_period) }}
    {% endif %}
),

customers as (
    select * from {{ ref('dim_customers') }}
),

dates as (
    select * from {{ ref('dim_date') }}
),

-- Join order items with products
product_orders as (
    select
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        p.product_category_name,
        p.product_category_name_english,
        oi.price,
        oi.freight_value,
        o.order_date,
        o.customer_id,
        o.order_status,
        d.year,
        d.month,
        d.quarter,
        d.season,
        d.is_festival_season
    from order_items oi
    inner join products p on oi.product_id = p.product_id
    inner join orders o on oi.order_id = o.order_id
    inner join dates d on cast(date_format(o.order_date, '%Y%m%d') as int) = d.date_key
    {% if product_categories != 'all' %}
    where p.product_category_name_english in ({{ product_categories }})
    {% endif %}
),

-- Product sales by time period
product_sales_by_time as (
    select
        product_id,
        product_category_name,
        product_category_name_english,
        year,
        month,
        count(*) as units_sold,
        sum(price) as total_sales,
        avg(price) as avg_price
    from product_orders
    group by 1, 2, 3, 4, 5
),

-- Product sales by region
product_sales_by_region as (
    select
        po.product_id,
        po.product_category_name,
        po.product_category_name_english,
        c.customer_state,
        count(*) as units_sold,
        sum(po.price) as total_sales
    from product_orders po
    inner join customers c on po.customer_id = c.customer_id
    group by 1, 2, 3, 4
),

-- Product sales by season
product_sales_by_season as (
    select
        product_id,
        product_category_name,
        product_category_name_english,
        season,
        is_festival_season,
        count(*) as units_sold,
        sum(price) as total_sales,
        avg(price) as avg_price
    from product_orders
    group by 1, 2, 3, 4, 5
),

-- Product affinity analysis (which products are purchased together)
product_pairs as (
    select
        a.product_id as product_a,
        b.product_id as product_b,
        a.product_category_name_english as category_a,
        b.product_category_name_english as category_b,
        count(distinct a.order_id) as times_purchased_together
    from product_orders a
    inner join product_orders b
        on a.order_id = b.order_id
        and a.product_id < b.product_id
    group by 1, 2, 3, 4
    having count(distinct a.order_id) > 1
),

-- Overall product performance
product_performance as (
    select
        p.product_id,
        p.product_category_name,
        p.product_category_name_english,
        count(distinct po.order_id) as order_count,
        count(po.order_item_id) as units_sold,
        sum(po.price) as total_sales,
        avg(po.price) as avg_price,
        sum(po.freight_value) as total_freight,
        count(distinct po.customer_id) as customer_count,
        count(distinct po.customer_id) / nullif(count(distinct po.order_id), 0) as avg_customers_per_order,
        -- Seasonal metrics
        sum(case when po.is_festival_season then po.price else 0 end) as festival_season_sales,
        sum(case when po.is_festival_season then 1 else 0 end) as festival_season_units,
        -- Calculate sales rank
        row_number() over (order by sum(po.price) desc) as sales_rank,
        -- Calculate units rank
        row_number() over (order by count(po.order_item_id) desc) as units_rank
    from products p
    left join product_orders po on p.product_id = po.product_id
    group by 1, 2, 3
)

select * from product_performance
```

3. Create a schema.yml file in the product_marts directory:

```yaml
# models/marts/product_marts/schema.yml
version: 2

models:
  - name: product_performance
    description: "Product performance analysis with sales trends and metrics"
    config:
      tags: ['product', 'analysis', 'mart']
    columns:
      - name: product_id
        description: "Primary key - unique identifier for the product"
        tests:
          - unique
          - not_null
      - name: product_category_name
        description: "Product category name in original language"
      - name: product_category_name_english
        description: "Product category name in English"
      - name: order_count
        description: "Number of orders containing this product"
      - name: units_sold
        description: "Total units sold"
      - name: total_sales
        description: "Total sales amount"
        tests:
          - values_in_range:
              min_value: 0
              max_value: 1000000
      - name: avg_price
        description: "Average price of the product"
      - name: total_freight
        description: "Total freight value for this product"
      - name: customer_count
        description: "Number of unique customers who purchased this product"
      - name: avg_customers_per_order
        description: "Average number of customers per order for this product"
      - name: festival_season_sales
        description: "Sales during festival season (Sep-Nov)"
      - name: festival_season_units
        description: "Units sold during festival season (Sep-Nov)"
      - name: sales_rank
        description: "Rank of product by total sales (1 is highest)"
        tests:
          - values_increasing:
              partition_by: 'null'
              order_by: 'sales_rank'
      - name: units_rank
        description: "Rank of product by units sold (1 is highest)"
        tests:
          - values_increasing:
              partition_by: 'null'
              order_by: 'units_rank'
```

4. Create a macro for date filtering:

```sql
-- macros/get_date_filter.sql
{% macro get_date_filter(date_column, period) %}
    {% if period == 'last_30_days' %}
        {{ date_column }} >= dateadd('day', -30, current_date())
    {% elif period == 'last_90_days' %}
        {{ date_column }} >= dateadd('day', -90, current_date())
    {% elif period == 'last_year' %}
        {{ date_column }} >= dateadd('year', -1, current_date())
    {% elif period == 'ytd' %}
        {{ date_column }} >= date_trunc('year', current_date())
    {% elif period == 'last_month' %}
        {{ date_column }} >= date_trunc('month', dateadd('month', -1, current_date())) and
        {{ date_column }} < date_trunc('month', current_date())
    {% else %}
        1=1
    {% endif %}
{% endmacro %}
```

### Key Points

- We use Jinja variables to make the analysis configurable
- We create multiple CTEs for different aspects of product performance
- We implement product affinity analysis to find products often purchased together
- We calculate seasonal metrics to identify trends
- We use window functions to rank products by sales and units
- We create a custom macro for flexible date filtering
- We implement comprehensive tests for the model

### Usage Examples

1. Run the model with default parameters:
```bash
dbt run -m product_performance
```

2. Run the model for a specific time period:
```bash
dbt run -m product_performance --vars '{"analysis_period": "last_90_days"}'
```

3. Run the model for specific product categories:
```bash
dbt run -m product_performance --vars '{"product_categories": ["furniture", "electronics", "clothing"]}'
```

4. Run the model with both parameters:
```bash
dbt run -m product_performance --vars '{"analysis_period": "last_year", "product_categories": ["furniture"]}'
```

This model provides a comprehensive view of product performance that can be used to identify top-selling products, seasonal trends, regional preferences, and product affinities. The configurable nature of the model allows business users to focus on specific time periods or product categories as needed.

# Module 4: ML Feature Engineering and Explainable Analytics - Exercise Solutions

This document provides detailed solutions for the exercises in Module 4 of the VyaparBazaar Analytics Internship Camp.

## Exercise 4.1: Enhance Customer Churn Features

### Solution

1. First, we examine the existing `customer_churn_features.sql` model to understand the current implementation.

2. Create the enhanced version `customer_churn_features_v2.sql`:

```sql
-- models/ml_features/customer_churn_features_v2.sql
{{
    config(
        materialized='table'
    )
}}

with orders as (
    select * from {{ ref('fct_orders') }}
),

order_items as (
    select * from {{ ref('fct_order_items') }}
),

products as (
    select * from {{ ref('dim_products') }}
),

refunds as (
    select * from {{ ref('stg_refunds') }}
),

clickstream as (
    select * from {{ ref('stg_clickstream') }}
),

-- Get base customer data
customers as (
    select * from {{ ref('dim_customers') }}
),

-- Calculate order metrics
customer_orders as (
    select
        customer_id,
        count(distinct order_id) as order_count,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        sum(order_total) as total_order_value,
        avg(order_total) as avg_order_value,

        -- New features
        count(distinct case
            when datediff('day', order_date, current_date()) <= 90
            then order_id
        end) as order_frequency_last_90_days,

        count(distinct case
            when datediff('day', order_date, current_date()) <= 30
            then order_id
        end) as order_frequency_last_30_days,

        sum(case
            when dayofweek(order_date) in (0, 6)
            then 1 else 0
        end)::float /
        nullif(count(order_id), 0) as weekend_shopper_ratio,

        sum(case
            when extract(hour from order_date) between 18 and 23
            then 1 else 0
        end)::float /
        nullif(count(order_id), 0) as evening_shopper_ratio
    from orders
    group by 1
),

-- Get order sequence for time between orders
order_sequence as (
    select
        customer_id,
        order_id,
        order_date,
        row_number() over (partition by customer_id order by order_date) as order_seq
    from orders
),

first_second_order as (
    select
        customer_id,
        max(case when order_seq = 1 then order_date end) as first_order_date,
        max(case when order_seq = 2 then order_date end) as second_order_date,
        datediff('day',
            max(case when order_seq = 1 then order_date end),
            max(case when order_seq = 2 then order_date end)
        ) as days_between_first_second_order
    from order_sequence
    group by 1
),

-- Calculate product diversity
product_diversity as (
    select
        o.customer_id,
        count(distinct p.product_category_name_english) as product_category_diversity
    from orders o
    join order_items oi on o.order_id = oi.order_id
    join products p on oi.product_id = p.product_id
    group by 1
),

-- Calculate refund metrics
refund_metrics as (
    select
        o.customer_id,
        max(case when r.refund_id is not null then 1 else 0 end) as has_returned_item,
        count(distinct r.refund_id)::float /
        nullif(count(distinct o.order_id), 0) as refund_rate
    from orders o
    left join refunds r on o.order_id = r.order_id
    group by 1
),

-- Calculate order value trend
recent_orders as (
    select
        customer_id,
        order_id,
        order_date,
        order_total,
        row_number() over (partition by customer_id order by order_date desc) as reverse_order_seq
    from orders
),

order_value_trends as (
    select
        customer_id,
        avg(case when reverse_order_seq <= 3 then order_total end) as recent_avg_order_value,
        avg(order_total) as all_time_avg_order_value,
        avg(case when reverse_order_seq <= 3 then order_total end) /
        nullif(avg(order_total), 0) as order_value_trend
    from recent_orders
    group by 1
),

-- Combine all features
customer_features as (
    select
        c.customer_id,

        -- Target variable
        case
            when datediff('day', co.last_order_date, current_date()) > 90
            then 1 else 0
        end as is_churned,

        -- Existing features
        datediff('day', co.last_order_date, current_date()) as days_since_last_order,
        co.order_count,
        co.total_order_value,
        co.avg_order_value,

        -- New features
        co.order_frequency_last_90_days,
        co.order_frequency_last_30_days,
        ovt.order_value_trend,
        fso.days_between_first_second_order,
        pd.product_category_diversity,
        rm.has_returned_item,
        rm.refund_rate,
        co.weekend_shopper_ratio,
        co.evening_shopper_ratio

    from customers c
    left join customer_orders co on c.customer_id = co.customer_id
    left join first_second_order fso on c.customer_id = fso.customer_id
    left join product_diversity pd on c.customer_id = pd.customer_id
    left join refund_metrics rm on c.customer_id = rm.customer_id
    left join order_value_trends ovt on c.customer_id = ovt.customer_id
)

select * from customer_features
```

3. Update the schema.yml file:

```yaml
# models/ml_features/schema.yml
version: 2

models:
  - name: customer_churn_features_v2
    description: "Enhanced features for predicting customer churn, with additional behavioral and temporal patterns"
    columns:
      - name: customer_id
        description: "Unique identifier for a customer"
        tests:
          - unique
          - not_null
      - name: is_churned
        description: "Target variable: 1 if customer has churned (no orders in 90+ days), 0 otherwise"
        tests:
          - not_null
          - accepted_values:
              values: [0, 1]
      - name: days_since_last_order
        description: "Number of days since the customer's last order"
      - name: order_count
        description: "Total number of orders placed by the customer"
      - name: total_order_value
        description: "Total amount spent by the customer across all orders"
      - name: avg_order_value
        description: "Average value of customer orders"
      - name: order_frequency_last_90_days
        description: "Number of orders placed in the last 90 days"
      - name: order_frequency_last_30_days
        description: "Number of orders placed in the last 30 days"
      - name: order_value_trend
        description: "Ratio of average order value in last 3 orders compared to all-time average (>1 means increasing, <1 means decreasing)"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              strictly: true
      - name: days_between_first_second_order
        description: "Number of days between the customer's first and second orders (null if fewer than 2 orders)"
      - name: product_category_diversity
        description: "Number of unique product categories purchased by the customer"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              strictly: true
      - name: has_returned_item
        description: "Boolean indicating if the customer has ever returned an item"
        tests:
          - accepted_values:
              values: [0, 1]
      - name: refund_rate
        description: "Percentage of orders that resulted in refunds"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1
              strictly_between: false
      - name: weekend_shopper_ratio
        description: "Percentage of orders placed on weekends"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1
              strictly_between: false
      - name: evening_shopper_ratio
        description: "Percentage of orders placed in evening hours (6 PM - midnight)"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1
              strictly_between: false
```

### Key Points

- We've organized the SQL into clear CTEs for readability and maintainability
- We've added temporal features that capture recent behavior (last 30/90 days)
- We've included features that capture customer preferences (weekend/evening shopping)
- We've added features related to product diversity and returns
- We've implemented comprehensive tests, especially for ratio features
- We've provided clear documentation for all features

## Exercise 4.2: Create Product Recommendation Features

### Solution

1. Create the `product_recommendation_features.sql` file:

```sql
-- models/ml_features/product_recommendation_features.sql
{{
    config(
        materialized='table'
    )
}}

with orders as (
    select * from {{ ref('fct_orders') }}
),

order_items as (
    select * from {{ ref('fct_order_items') }}
),

products as (
    select * from {{ ref('dim_products') }}
),

clickstream as (
    select * from {{ ref('stg_clickstream') }}
),

-- Get all customer-product pairs from orders
customer_products as (
    select
        o.customer_id,
        oi.product_id,
        p.product_category_name_english,
        count(distinct o.order_id) as purchase_count,
        sum(oi.price) as total_spent,
        max(o.order_date) as last_purchase_date,
        datediff('day', max(o.order_date), current_date()) as days_since_last_purchase
    from orders o
    join order_items oi on o.order_id = oi.order_id
    join products p on oi.product_id = p.product_id
    group by 1, 2, 3
),

-- Calculate category preferences
category_preferences as (
    select
        customer_id,
        product_category_name_english,
        count(distinct product_id) as category_product_count,
        row_number() over (
            partition by customer_id
            order by count(distinct product_id) desc
        ) as category_rank
    from customer_products
    group by 1, 2
),

-- Calculate co-purchase patterns
copurchases as (
    select
        oi1.product_id,
        oi2.product_id as copurchased_product_id,
        o.customer_id,
        count(distinct o.order_id) as copurchase_count
    from orders o
    join order_items oi1 on o.order_id = oi1.order_id
    join order_items oi2 on o.order_id = oi2.order_id
    where oi1.product_id != oi2.product_id
    group by 1, 2, 3
),

-- Aggregate co-purchases by product
product_copurchases as (
    select
        customer_id,
        product_id,
        sum(copurchase_count) as copurchase_count
    from copurchases
    group by 1, 2
),

-- Get product views from clickstream
product_views as (
    select
        customer_id,
        cast(json_extract(event_details, '$.product_id') as varchar) as product_id,
        count(*) as view_count,
        sum(case when event_type = 'add_to_cart' then 1 else 0 end) as cart_count
    from clickstream
    where event_type in ('product_view', 'add_to_cart')
    and customer_id is not null
    and json_extract(event_details, '$.product_id') is not null
    group by 1, 2
),

-- Combine all features
recommendation_features as (
    select
        cp.customer_id,
        cp.product_id,
        cp.product_category_name_english,
        cp.purchase_count,
        cp.total_spent,
        cp.days_since_last_purchase,
        coalesce(cat.category_rank, 999) as category_rank,
        coalesce(pc.copurchase_count, 0) as copurchase_count,
        coalesce(pv.view_count, 0) as view_count,
        coalesce(pv.cart_count, 0) as cart_count,
        case
            when pv.view_count > 0
            then cp.purchase_count::float / pv.view_count
            else 0
        end as purchase_to_view_ratio
    from customer_products cp
    left join category_preferences cat on
        cp.customer_id = cat.customer_id and
        cp.product_category_name_english = cat.product_category_name_english
    left join product_copurchases pc on
        cp.customer_id = pc.customer_id and
        cp.product_id = pc.product_id
    left join product_views pv on
        cp.customer_id = pv.customer_id and
        cp.product_id = pv.product_id
)

select * from recommendation_features
```

2. Create the schema.yml file:

```yaml
# models/ml_features/schema.yml (addition)
  - name: product_recommendation_features
    description: "Features for product recommendation systems"
    columns:
      - name: customer_id
        description: "Customer identifier"
        tests:
          - not_null
      - name: product_id
        description: "Product identifier"
        tests:
          - not_null
      - name: product_category_name_english
        description: "Product category name in English"
      - name: purchase_count
        description: "Number of times the customer purchased this product"
        tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 1
              strictly: true
      - name: total_spent
        description: "Total amount spent by the customer on this product"
        tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              strictly: true
      - name: days_since_last_purchase
        description: "Number of days since the customer last purchased this product"
      - name: category_rank
        description: "Rank of this category in the customer's preferences (based on purchase count)"
      - name: copurchase_count
        description: "Number of times this product was purchased with other products"
      - name: view_count
        description: "Number of times the customer viewed this product"
      - name: cart_count
        description: "Number of times the customer added this product to cart"
      - name: purchase_to_view_ratio
        description: "Ratio of purchases to views for this product"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1
              strictly_between: false
```

### Key Points

- We've created features at the customer-product level
- We've included purchase history, viewing behavior, and category preferences
- We've calculated co-purchase patterns to identify related products
- We've added conversion metrics like purchase-to-view ratio
- We've implemented appropriate tests for all features
- We've provided clear documentation for all features

## Exercise 4.3: Build Customer Segmentation Features

### Solution

1. Create the `customer_segmentation_features.sql` file:

```sql
-- models/ml_features/customer_segmentation_features.sql
{{
    config(
        materialized='table'
    )
}}

with orders as (
    select * from {{ ref('fct_orders') }}
),

order_items as (
    select * from {{ ref('fct_order_items') }}
),

products as (
    select * from {{ ref('dim_products') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
),

reviews as (
    select * from {{ ref('stg_reviews') }}
),

clickstream as (
    select * from {{ ref('stg_clickstream') }}
),

-- Get base customer data
customers as (
    select * from {{ ref('dim_customers') }}
),

-- Calculate RFM metrics
rfm_metrics as (
    select
        customer_id,
        datediff('day', max(order_date), current_date()) as recency_days,
        count(distinct order_id) as frequency,
        avg(order_total) as monetary_value
    from orders
    group by 1
),

-- Calculate product category preferences
category_preferences as (
    select
        o.customer_id,
        p.product_category_name_english,
        count(distinct oi.order_item_id) as category_purchase_count,
        row_number() over (
            partition by o.customer_id
            order by count(distinct oi.order_item_id) desc
        ) as category_rank
    from orders o
    join order_items oi on o.order_id = oi.order_id
    join products p on oi.product_id = p.product_id
    group by 1, 2
),

preferred_categories as (
    select
        customer_id,
        max(case when category_rank = 1 then product_category_name_english end) as preferred_product_category,
        max(category_purchase_count) as top_category_purchases,
        sum(category_purchase_count) as total_category_purchases,
        max(category_purchase_count)::float / nullif(sum(category_purchase_count), 0) as category_loyalty
    from category_preferences
    group by 1
),

-- Calculate payment method preferences
payment_preferences as (
    select
        o.customer_id,
        p.payment_type,
        count(distinct p.payment_id) as payment_type_count,
        row_number() over (
            partition by o.customer_id
            order by count(distinct p.payment_id) desc
        ) as payment_rank
    from orders o
    join payments p on o.order_id = p.order_id
    group by 1, 2
),

preferred_payments as (
    select
        customer_id,
        max(case when payment_rank = 1 then payment_type end) as preferred_payment_method,
        sum(case when payment_type = 'voucher' or payment_type = 'discount_code' then payment_type_count else 0 end)::float /
        nullif(sum(payment_type_count), 0) > 0.5 as discount_hunter,
        sum(case when payment_type = 'credit_card' and payment_installments > 1 then payment_type_count else 0 end)::float /
        nullif(sum(payment_type_count), 0) > 0.5 as installment_payer
    from payment_preferences
    group by 1
),

-- Calculate review behavior
review_behavior as (
    select
        o.customer_id,
        avg(r.review_score) as average_review_score
    from orders o
    join reviews r on o.order_id = r.order_id
    group by 1
),

-- Calculate device and browser preferences
device_preferences as (
    select
        customer_id,
        device,
        browser,
        count(*) as event_count,
        row_number() over (partition by customer_id order by count(*) desc) as device_rank,
        row_number() over (partition by customer_id order by count(*) desc) as browser_rank
    from clickstream
    where customer_id is not null
    group by 1, 2, 3
),

preferred_devices as (
    select
        customer_id,
        max(case when device_rank = 1 then device end) as device_preference,
        max(case when browser_rank = 1 then browser end) as browser_preference,
        avg(extract(epoch from (session_end - session_start)) / 60) as session_duration_avg
    from (
        select
            customer_id,
            device,
            browser,
            session_id,
            min(event_timestamp) as session_start,
            max(event_timestamp) as session_end
        from clickstream
        where customer_id is not null
        group by 1, 2, 3, 4
    )
    group by 1
),

-- Calculate purchase patterns
purchase_patterns as (
    select
        customer_id,
        sum(case when dayofweek(order_date) in (0, 6) then 1 else 0 end)::float /
        nullif(count(order_id), 0) > 0.5 as weekend_shopper,
        sum(case when extract(hour from order_date) between 18 and 23 then 1 else 0 end)::float /
        nullif(count(order_id), 0) > 0.5 as evening_shopper
    from orders
    group by 1
),

-- Combine all features
segmentation_features as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,

        -- RFM features
        r.recency_days,
        r.frequency,
        r.monetary_value,

        -- Category preferences
        pc.preferred_product_category,
        pc.category_loyalty,

        -- Payment preferences
        pp.preferred_payment_method,
        pp.discount_hunter,
        pp.installment_payer,

        -- Review behavior
        rb.average_review_score,

        -- Device preferences
        pd.device_preference,
        pd.browser_preference,
        pd.session_duration_avg,

        -- Purchase patterns
        pat.weekend_shopper,
        pat.evening_shopper

    from customers c
    left join rfm_metrics r on c.customer_id = r.customer_id
    left join preferred_categories pc on c.customer_id = pc.customer_id
    left join preferred_payments pp on c.customer_id = pp.customer_id
    left join review_behavior rb on c.customer_id = rb.customer_id
    left join preferred_devices pd on c.customer_id = pd.customer_id
    left join purchase_patterns pat on c.customer_id = pat.customer_id
)

select * from segmentation_features
```

2. Create the schema.yml file:

```yaml
# models/ml_features/schema.yml (addition)
  - name: customer_segmentation_features
    description: "Features for customer segmentation analysis"
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
      - name: recency_days
        description: "Days since last order (recency component of RFM)"
      - name: frequency
        description: "Number of orders (frequency component of RFM)"
      - name: monetary_value
        description: "Average order value (monetary component of RFM)"
      - name: preferred_product_category
        description: "Most frequently purchased product category"
      - name: category_loyalty
        description: "Percentage of purchases in top category"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1
              strictly_between: false
      - name: preferred_payment_method
        description: "Most frequently used payment method"
      - name: discount_hunter
        description: "Boolean, true if >50% of purchases used promotions"
        tests:
          - accepted_values:
              values: [true, false]
      - name: installment_payer
        description: "Boolean, true if >50% of purchases used installments"
        tests:
          - accepted_values:
              values: [true, false]
      - name: average_review_score
        description: "Average review score given by the customer"
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 1
              max_value: 5
              strictly_between: false
      - name: device_preference
        description: "Most commonly used device"
      - name: browser_preference
        description: "Most commonly used browser"
      - name: session_duration_avg
        description: "Average session duration in minutes"
      - name: weekend_shopper
        description: "Boolean, true if >50% of orders are on weekends"
        tests:
          - accepted_values:
              values: [true, false]
      - name: evening_shopper
        description: "Boolean, true if >50% of orders are in evening hours"
        tests:
          - accepted_values:
              values: [true, false]
```

### Key Points

- We've created a comprehensive set of features for customer segmentation
- We've included RFM metrics which are fundamental for segmentation
- We've added behavioral features like device preferences and shopping patterns
- We've included categorical features like preferred product categories and payment methods
- We've implemented appropriate tests for all features
- We've provided clear documentation for all features

## Exercise 4.4: Implement Feature Documentation and Testing

### Solution

1. First, we create the custom generic tests:

```sql
-- tests/generic/test_correlation_with_target.sql
{% test correlation_with_target(model, column_name, target_column, min_correlation=0.05, absolute=true) %}

with feature_data as (
    select
        {{ column_name }} as feature_value,
        {{ target_column }} as target_value
    from {{ model }}
    where {{ column_name }} is not null
),

correlation_calc as (
    select
        (avg(feature_value * target_value) - (avg(feature_value) * avg(target_value))) /
        (stddev(feature_value) * stddev(target_value)) as correlation
    from feature_data
)

select *
from correlation_calc
where
{% if absolute %}
    abs(correlation) < {{ min_correlation }}
{% else %}
    correlation < {{ min_correlation }}
{% endif %}

{% endtest %}
```

```sql
-- tests/generic/test_feature_variance.sql
{% test feature_variance(model, column_name, min_variance=0.01) %}

with feature_stats as (
    select
        var_pop({{ column_name }}) as feature_variance
    from {{ model }}
    where {{ column_name }} is not null
)

select *
from feature_stats
where feature_variance < {{ min_variance }}

{% endtest %}
```

2. Update the schema.yml file to apply these tests:

```yaml
# models/ml_features/schema.yml (additions)
  - name: customer_churn_features_v2
    columns:
      - name: days_since_last_order
        tests:
          - correlation_with_target:
              target_column: is_churned
              min_correlation: 0.1
              absolute: true
          - feature_variance:
              min_variance: 0.1
      - name: order_frequency_last_90_days
        tests:
          - correlation_with_target:
              target_column: is_churned
              min_correlation: 0.1
              absolute: true
          - feature_variance:
              min_variance: 0.1
      - name: refund_rate
        tests:
          - correlation_with_target:
              target_column: is_churned
              min_correlation: 0.05
              absolute: true
```

3. Add comprehensive documentation to all features:

```yaml
# models/ml_features/schema.yml (enhanced documentation example)
  - name: customer_churn_features_v2
    description: >
      Enhanced features for predicting customer churn, with additional behavioral and temporal patterns.
      This model is designed to provide a comprehensive view of customer behavior that can be used to
      predict the likelihood of churn, defined as no orders in the past 90 days.
    columns:
      - name: customer_id
        description: "Unique identifier for a customer"
        tests:
          - unique
          - not_null
      - name: is_churned
        description: >
          Target variable: 1 if customer has churned (no orders in 90+ days), 0 otherwise.
          This is the variable we're trying to predict with our model.
        tests:
          - not_null
          - accepted_values:
              values: [0, 1]
      - name: days_since_last_order
        description: >
          Number of days since the customer's last order. This is a key recency metric
          and typically has a strong correlation with churn probability. The longer a customer
          has been inactive, the more likely they are to have churned.
          Expected range: 0 to several hundred days.
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              strictly: true
          - correlation_with_target:
              target_column: is_churned
              min_correlation: 0.1
              absolute: true
```

### Key Points

- We've created custom tests to validate feature quality
- We've enhanced documentation with business context and expected ranges
- We've applied correlation tests to ensure features are predictive
- We've applied variance tests to ensure features have sufficient information
- We've provided comprehensive documentation that explains the purpose and context of each feature

## Exercise 4.5: Create an Explainable AI Demo

### Solution

Create the `explainable_ai_demo.py` script:

```python
"""
Explainable AI Demo for VyaparBazaar Analytics.

This script demonstrates how to use the ML features generated by the dbt models
to build explainable AI models for customer churn prediction.
"""

import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import shap

# Connect to DuckDB
print("Connecting to DuckDB...")
con = duckdb.connect('data/vyaparbazaar.duckdb')

# Load churn features
print("Loading customer churn features...")
churn_features_df = con.execute("""
    SELECT * FROM customer_churn_features_v2
""").fetchdf()

# Display basic information
print(f"Loaded {len(churn_features_df)} customer records")
print(f"Churn rate: {churn_features_df['is_churned'].mean():.2%}")

# Prepare data for modeling
print("\nPreparing data for modeling...")
# Drop identifier columns and handle missing values
X = churn_features_df.drop(['customer_id', 'is_churned'], axis=1)
y = churn_features_df['is_churned']

# Fill missing values
X = X.fillna(0)

# Split data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Training set: {X_train.shape[0]} records")
print(f"Test set: {X_test.shape[0]} records")

# Train a Random Forest model
print("\nTraining Random Forest model...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate the model
print("\nEvaluating model performance...")
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Plot feature importance
print("\nCalculating feature importance...")
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

plt.figure(figsize=(10, 6))
sns.barplot(x='importance', y='feature', data=feature_importance.head(10))
plt.title('Top 10 Features by Importance')
plt.tight_layout()
plt.savefig('feature_importance.png')
print("Feature importance plot saved as 'feature_importance.png'")

# Generate SHAP values for explainability
print("\nGenerating SHAP values for model explanation...")
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Plot SHAP summary
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values[1], X_test, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig('shap_summary.png')
print("SHAP summary plot saved as 'shap_summary.png'")

# Generate explanations for a few examples
print("\nExample Churn Predictions with Explanations:")
for i in range(min(5, len(X_test))):
    prediction = model.predict_proba(X_test.iloc[i:i+1])[0, 1]
    print(f"\nCustomer {i+1}:")
    print(f"Churn Probability: {prediction:.2f}")

    # Get top contributing features
    instance_shap_values = explainer.shap_values(X_test.iloc[i:i+1])[1][0]
    feature_names = X_test.columns
    feature_importance = list(zip(feature_names, instance_shap_values))
    feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

    print("Top contributing factors:")
    for feature, value in feature_importance[:5]:
        direction = "increases" if value > 0 else "decreases"
        print(f"  - {feature}: {abs(value):.4f} ({direction} churn probability)")

    # Get actual feature values for this customer
    print("Key metrics for this customer:")
    for feature, _ in feature_importance[:5]:
        print(f"  - {feature}: {X_test.iloc[i][feature]}")

print("\nExplainable AI demo completed!")
```

### Key Points

- We've created a script that loads features from DuckDB
- We've implemented a Random Forest model for churn prediction
- We've used SHAP values to explain model predictions
- We've visualized feature importance and SHAP values
- We've provided example explanations for individual predictions
- We've included comments explaining each step of the process
# Module 4: ML Feature Engineering and Explainable Analytics 🚀

Welcome to Module 4 of the VyaparBazaar Analytics Internship Camp! In this module, we'll explore how to leverage our well-structured data models to create machine learning-ready features and build explainable analytics. You'll learn how to bridge the gap between data modeling and data science, all while maintaining the principles of modularity, testability, and documentation that make dbt so powerful.

## 🎯 Learning Objectives

By the end of this module, you will be able to:
- Design and implement ML feature models in dbt
- Apply feature engineering techniques to transform business data into ML-ready features
- Create comprehensive documentation for ML features
- Implement testing strategies for ML feature models
- Understand the principles of explainable AI and how to apply them
- Build a foundation for integrating ML models with your dbt pipeline

## 🧠 Introduction to ML Feature Engineering

### What is Feature Engineering?

Feature engineering is the process of transforming raw data into features that better represent the underlying problem to predictive models, resulting in improved model accuracy on unseen data.

In the context of dbt and analytics engineering:
- **Feature Models**: SQL transformations that prepare data specifically for machine learning use cases
- **Feature Tables**: The materialized output of feature models, ready to be consumed by ML algorithms
- **Feature Documentation**: Clear descriptions of what each feature represents and how it's calculated

### The ML Feature Layer in dbt

The ML feature layer sits at the top of our modeling hierarchy:

```
Raw Data → Staging Models → Intermediate Models → Mart Models → ML Feature Models
```

ML feature models typically:
- Combine data from multiple mart models
- Apply specific transformations needed for ML (scaling, encoding, etc.)
- Create target variables for supervised learning
- Generate features that capture business knowledge and domain expertise

## 🛠️ Feature Engineering Techniques in SQL

### Temporal Features

Time-based features are crucial for many predictive models:

```sql
-- Days since last order
datediff('day', max(order_date), current_date()) as days_since_last_order,

-- Order frequency (orders per month)
count(distinct order_id)::float / 
  nullif(datediff('month', min(order_date), current_date()), 0) as orders_per_month,

-- Is weekend shopper
sum(case when dayofweek(order_date) in (0, 6) then 1 else 0 end)::float / 
  nullif(count(order_id), 0) as weekend_order_ratio
```

### Aggregation Features

Aggregations help capture patterns in customer behavior:

```sql
-- Average order value
avg(order_total) as avg_order_value,

-- Order value variability
stddev(order_total) as order_value_stddev,

-- Percentage of canceled orders
sum(case when order_status = 'canceled' then 1 else 0 end)::float / 
  nullif(count(order_id), 0) as cancel_rate
```

### Ratio and Rate Features

Ratios often provide more predictive power than raw counts:

```sql
-- Cart abandonment rate
(count(distinct cart_id) - count(distinct order_id))::float / 
  nullif(count(distinct cart_id), 0) as cart_abandonment_rate,

-- Product return rate
sum(is_returned)::float / nullif(count(order_item_id), 0) as return_rate
```

### Categorical Encoding

Transforming categorical variables into numeric representations:

```sql
-- One-hot encoding for payment methods
max(case when payment_type = 'credit_card' then 1 else 0 end) as used_credit_card,
max(case when payment_type = 'debit_card' then 1 else 0 end) as used_debit_card,
max(case when payment_type = 'upi' then 1 else 0 end) as used_upi,
max(case when payment_type = 'cod' then 1 else 0 end) as used_cod
```

### RFM Features

Recency, Frequency, and Monetary value are powerful predictors:

```sql
-- Recency: days since last order
datediff('day', max(order_date), current_date()) as recency_days,

-- Frequency: number of orders
count(distinct order_id) as frequency,

-- Monetary: average order value
avg(order_total) as monetary_value
```

## 📊 Building ML Feature Models in dbt

### Structure of an ML Feature Model

ML feature models follow a similar structure to other dbt models but with a focus on creating features:

```sql
-- models/ml_features/customer_churn_features.sql
{{
    config(
        materialized='table'
    )
}}

with customer_orders as (
    select * from {{ ref('fct_orders') }}
),

customer_behavior as (
    select * from {{ ref('customer_behavior') }}
),

customer_features as (
    select
        c.customer_id,
        
        -- Target variable
        case 
            when datediff('day', max(o.order_date), current_date()) > 90 
            then 1 else 0 
        end as is_churned,
        
        -- Recency features
        datediff('day', max(o.order_date), current_date()) as days_since_last_order,
        
        -- Frequency features
        count(distinct o.order_id) as order_count,
        
        -- Monetary features
        avg(o.order_total) as avg_order_value,
        sum(o.order_total) as total_spent,
        
        -- Behavioral features
        b.cart_abandonment_rate,
        b.product_view_count,
        b.search_count
        
    from {{ ref('dim_customers') }} c
    left join customer_orders o on c.customer_id = o.customer_id
    left join customer_behavior b on c.customer_id = b.customer_id
    group by 1, b.cart_abandonment_rate, b.product_view_count, b.search_count
)

select * from customer_features
```

### Documenting ML Features

Proper documentation is crucial for ML features:

```yaml
# models/ml_features/schema.yml
version: 2

models:
  - name: customer_churn_features
    description: "Features for predicting customer churn, defined as customers who haven't ordered in 90+ days"
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
```

## 🧪 Testing ML Feature Models

Testing is especially important for ML features to ensure model reliability:

### Data Quality Tests

```yaml
# models/ml_features/schema.yml
columns:
  - name: avg_order_value
    description: "Average value of customer orders"
    tests:
      - not_null
      - dbt_expectations.expect_column_values_to_be_between:
          min_value: 0
          strictly: true
```

### Custom Tests for ML Features

```sql
-- tests/generic/test_values_in_range.sql
{% test values_in_range(model, column_name, min_value, max_value) %}
    select *
    from {{ model }}
    where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
```

## 🔍 Explainable Analytics

Explainable analytics focuses on making data insights and ML predictions understandable to business users.

### Key Principles of Explainable Analytics:

1. **Transparency**: Clear documentation of how features are calculated
2. **Interpretability**: Features should have clear business meaning
3. **Traceability**: Ability to trace predictions back to source data
4. **Simplicity**: Prefer simpler, more interpretable models when possible

### Implementing Explainable Analytics in dbt:

1. **Feature Documentation**: Comprehensive descriptions of what each feature represents
2. **Feature Lineage**: Clear data lineage showing how features are derived
3. **Business Context**: Connecting features to business metrics and KPIs
4. **Validation**: Tests that ensure features behave as expected

## 🚀 Real-world Use Cases

### Customer Churn Prediction

Predicting which customers are likely to stop purchasing:

```sql
-- Target variable definition
case 
    when datediff('day', max(order_date), current_date()) > 90 
    then 1 else 0 
end as is_churned
```

Key features:
- Recency of last purchase
- Order frequency and consistency
- Customer satisfaction metrics
- Product return rate
- Support ticket history

### Customer Lifetime Value Prediction

Forecasting the future value of customers:

```sql
-- Current LTV calculation
sum(order_total) as current_ltv
```

Key features:
- Purchase history trends
- Average order value growth
- Product category preferences
- Seasonal purchasing patterns
- Response to promotions

### Customer Segmentation

Grouping customers based on behavior:

```sql
-- RFM segmentation
case
    when recency_days <= 30 and frequency >= 3 and monetary_value >= 1000
    then 'High Value'
    when recency_days <= 60 and frequency >= 2
    then 'Mid Value'
    else 'Low Value'
end as customer_segment
```

### Product Recommendations

Identifying products a customer might be interested in:

```sql
-- Product affinity score
count(distinct case when p1.product_id = X and p2.product_id = Y 
      and p1.order_id = p2.order_id then p1.order_id end)::float / 
nullif(count(distinct case when p1.product_id = X 
      then p1.order_id end), 0) as product_affinity
```

## 🔄 Integrating with Python for ML

While dbt handles feature engineering, Python is typically used for model training:

```python
# Example Python code that would use the dbt-generated features
import duckdb
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import shap

# Connect to DuckDB
con = duckdb.connect('data/vyaparbazaar.duckdb')

# Load features
features_df = con.execute("""
    SELECT * FROM customer_churn_features
""").fetchdf()

# Prepare data
X = features_df.drop(['customer_id', 'is_churned'], axis=1)
y = features_df['is_churned']

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Explain predictions with SHAP
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
```

## 🎯 Best Practices for ML Feature Engineering in dbt

1. **Create dedicated feature models**: Keep feature engineering separate from analytics models
2. **Document extensively**: Each feature should have a clear description and business purpose
3. **Test rigorously**: Implement tests for value ranges, nulls, and business logic
4. **Maintain lineage**: Use refs to clearly show where features come from
5. **Version features**: Consider how to handle feature evolution over time
6. **Balance complexity**: More complex features aren't always better
7. **Consider performance**: Optimize heavy transformations for production use

## 🔮 What's Next?

After completing this module, you'll be ready to:
- Create sophisticated ML feature models
- Document and test your features properly
- Understand how to integrate with ML workflows
- Apply explainable analytics principles to your work

In the final project, you'll have the opportunity to apply all these concepts to create a complete analytics solution with ML-ready features.

## 📚 Additional Resources

- [Feature Engineering for Machine Learning](https://www.oreilly.com/library/view/feature-engineering-for/9781491953235/)
- [Interpretable Machine Learning](https://christophm.github.io/interpretable-ml-book/)
- [SHAP: SHapley Additive exPlanations](https://github.com/slundberg/shap)
- [dbt-ml-preprocessing](https://github.com/omnata-labs/dbt-ml-preprocessing)
- [Explainable AI Techniques](https://cloud.google.com/explainable-ai)

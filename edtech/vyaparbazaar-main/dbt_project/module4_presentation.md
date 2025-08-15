# 🧠 Module 4: ML Feature Engineering and Explainable Analytics

## Bridging the Gap Between Data Modeling and Data Science

---

## 🎯 Learning Objectives

By the end of this module, you will be able to:

- Design and implement ML feature models in dbt
- Apply feature engineering techniques to transform business data
- Create comprehensive documentation for ML features
- Implement testing strategies for ML feature models
- Understand the principles of explainable AI
- Build a foundation for integrating ML models with your dbt pipeline

---

## 🤔 What is Feature Engineering?

The process of transforming raw data into features that better represent the underlying problem to predictive models.

**In dbt context:**
- SQL transformations that prepare data for ML use cases
- Materialized tables ready for consumption by ML algorithms
- Documentation of what each feature represents

---

## 🏗️ The ML Feature Layer

```
Raw Data → Staging → Intermediate → Marts → ML Features
```

**ML feature models typically:**
- Combine data from multiple mart models
- Apply specific transformations for ML
- Create target variables for supervised learning
- Encode business knowledge into features

---

## ⏱️ Temporal Features

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

---

## 📊 Aggregation Features

```sql
-- Average order value
avg(order_total) as avg_order_value,

-- Order value variability
stddev(order_total) as order_value_stddev,

-- Percentage of canceled orders
sum(case when order_status = 'canceled' then 1 else 0 end)::float / 
  nullif(count(order_id), 0) as cancel_rate
```

---

## 📈 Ratio and Rate Features

```sql
-- Cart abandonment rate
(count(distinct cart_id) - count(distinct order_id))::float / 
  nullif(count(distinct cart_id), 0) as cart_abandonment_rate,

-- Product return rate
sum(is_returned)::float / nullif(count(order_item_id), 0) as return_rate
```

---

## 🔄 Categorical Encoding

```sql
-- One-hot encoding for payment methods
max(case when payment_type = 'credit_card' then 1 else 0 end) as used_credit_card,
max(case when payment_type = 'debit_card' then 1 else 0 end) as used_debit_card,
max(case when payment_type = 'upi' then 1 else 0 end) as used_upi,
max(case when payment_type = 'cod' then 1 else 0 end) as used_cod
```

---

## 🛒 RFM Features

```sql
-- Recency: days since last order
datediff('day', max(order_date), current_date()) as recency_days,

-- Frequency: number of orders
count(distinct order_id) as frequency,

-- Monetary: average order value
avg(order_total) as monetary_value
```

---

## 📝 Structure of an ML Feature Model

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
        sum(o.order_total) as total_spent
        
    from {{ ref('dim_customers') }} c
    left join customer_orders o on c.customer_id = o.customer_id
    group by 1
)

select * from customer_features
```

---

## 📚 Documenting ML Features

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

---

## 🧪 Testing ML Feature Models

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

---

## 🔍 Custom Tests for ML Features

```sql
-- tests/generic/test_correlation_with_target.sql
{% test correlation_with_target(model, column_name, target_column, min_correlation=0.05, absolute=true) %}
    select *
    from (
        select
            (avg({{ column_name }} * {{ target_column }}) - 
             (avg({{ column_name }}) * avg({{ target_column }}))) / 
            (stddev({{ column_name }}) * stddev({{ target_column }})) as correlation
        from {{ model }}
        where {{ column_name }} is not null
    )
    where 
    {% if absolute %}
        abs(correlation) < {{ min_correlation }}
    {% else %}
        correlation < {{ min_correlation }}
    {% endif %}
{% endtest %}
```

---

## 🔍 Explainable Analytics

Making data insights and ML predictions understandable to business users.

**Key Principles:**
1. **Transparency**: Clear documentation of feature calculations
2. **Interpretability**: Features with clear business meaning
3. **Traceability**: Ability to trace predictions back to source data
4. **Simplicity**: Prefer simpler, more interpretable models

---

## 🚀 Real-world Use Cases

### Customer Churn Prediction

```sql
-- Target variable definition
case 
    when datediff('day', max(order_date), current_date()) > 90 
    then 1 else 0 
end as is_churned
```

### Customer Lifetime Value Prediction

```sql
-- Current LTV calculation
sum(order_total) as current_ltv
```

### Customer Segmentation

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

---

## 🔄 Integrating with Python for ML

```python
# Example Python code using dbt-generated features
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

# Train model
X = features_df.drop(['customer_id', 'is_churned'], axis=1)
y = features_df['is_churned']
model = RandomForestClassifier().fit(X, y)

# Explain predictions with SHAP
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
```

---

## 📊 SHAP Values for Explainability

![SHAP Summary Plot](https://shap.readthedocs.io/en/latest/_images/shap_summary_plot.png)

SHAP (SHapley Additive exPlanations) values help explain individual predictions:
- How much each feature contributes to a prediction
- Whether the contribution is positive or negative
- Which features are most important overall

---

## 🧠 Hands-on Exercises

### Exercise 4.1: Enhance Customer Churn Features
- Add temporal, behavioral, and preference features

### Exercise 4.2: Create Product Recommendation Features
- Build customer-product level features

### Exercise 4.3: Build Customer Segmentation Features
- Implement RFM and behavioral segmentation

### Exercise 4.4: Implement Feature Documentation and Testing
- Add comprehensive tests and documentation

### Exercise 4.5: Create an Explainable AI Demo
- Build a Python script using SHAP for explanations

---

## 🎯 Best Practices

1. **Create dedicated feature models**: Separate from analytics models
2. **Document extensively**: Clear description and business purpose
3. **Test rigorously**: Value ranges, nulls, and business logic
4. **Maintain lineage**: Clear references to source models
5. **Version features**: Plan for feature evolution
6. **Balance complexity**: Simpler features are often better
7. **Consider performance**: Optimize for production use

---

## 🚀 Real-world Impact

- **Better Predictions**: Well-engineered features improve model accuracy
- **Business Understanding**: Features with clear meaning drive adoption
- **Faster Development**: Reusable features accelerate ML projects
- **Regulatory Compliance**: Explainable models meet regulatory requirements
- **Trust**: Stakeholders trust models they can understand

---

## 🎯 Key Takeaways

1. **Feature Engineering** is critical for ML success
2. **dbt** provides an excellent platform for feature creation
3. **Documentation and Testing** ensure feature quality
4. **Explainability** builds trust in ML models
5. **Integration** between dbt and Python enables end-to-end ML pipelines

---

## 🔮 What's Next?

In the **Final Project**, you'll apply all these concepts to:
- Create a complete analytics solution
- Build ML-ready features
- Implement explainable predictions
- Present insights to stakeholders

---

## 🙋 Questions?

Let's discuss!

---

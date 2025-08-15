# Module 5: Analytics Engineering Best Practices
## VyaparBazaar Analytics Internship Camp

---

## Learning Objectives

By the end of this module, students will be able to:
- Apply optimization techniques to improve model performance
- Choose appropriate materialization strategies for different use cases
- Understand deployment and scheduling considerations
- Effectively collaborate with stakeholders
- Build production-ready analytics pipelines

---

## Module Overview

1. Optimization Techniques
2. Materialization Strategies
3. Deployment and Scheduling
4. Working with Stakeholders
5. Hands-on Exercises

---

## 1. Optimization Techniques

---

### Query Performance Optimization

- **Use CTEs Effectively**
  - Improve readability
  - Organize complex logic
  - Be mindful of CTE overuse

---

### Filter Early, Join Late

```sql
-- Less efficient: Filtering after join
select o.order_id, c.customer_name
from orders o
join customers c on o.customer_id = c.customer_id
where o.order_date >= '2023-01-01'

-- More efficient: Filtering before join
with filtered_orders as (
    select order_id, customer_id
    from orders
    where order_date >= '2023-01-01'
)
select fo.order_id, c.customer_name
from filtered_orders fo
join customers c on fo.customer_id = c.customer_id
```

---

### Avoid SELECT *

```sql
-- Avoid this
select * from orders

-- Better approach
select
    order_id,
    customer_id,
    order_date,
    order_total
from orders
```

---

### Use Appropriate Aggregations

```sql
select
    customer_id,
    count(*) as order_count,                -- Fast
    approx_distinct(product_id) as approx_unique_products,  -- Faster
    count(distinct product_id) as exact_unique_products     -- Expensive
from order_items
group by 1
```

---

### Model Optimization Strategies

1. **Incremental Models**
2. **Partitioning and Clustering**
3. **Ephemeral Models for Intermediate Steps**

---

### Incremental Models

```sql
{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

select
    event_id,
    customer_id,
    event_timestamp
from {{ source('raw', 'clickstream') }}

{% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
{% endif %}
```

---

### Partitioning and Clustering

```sql
{{
    config(
        materialized='table',
        partition_by={
            "field": "order_date",
            "data_type": "date",
            "granularity": "month"
        },
        cluster_by=["customer_id", "order_status"]
    )
}}
```

---

### Ephemeral Models

```sql
{{
    config(
        materialized='ephemeral'
    )
}}

select
    customer_id,
    lower(trim(customer_email)) as normalized_email
from {{ ref('stg_customers') }}
```

---

## 2. Materialization Strategies

---

### Types of Materializations

| Type | Description | Best For |
|------|-------------|----------|
| View | Virtual table, computed on query | Small datasets, development |
| Table | Physical table, computed on run | Frequently queried data |
| Incremental | Updates only new/changed data | Large tables with frequent updates |
| Ephemeral | Compiled into dependent models | Simple intermediate transformations |

---

### View Materialization

**Pros:**
- No storage required
- Always up-to-date
- Fast to create

**Cons:**
- Can be slow for complex queries
- Recomputed every time

```sql
{{ config(materialized='view') }}
```

---

### Table Materialization

**Pros:**
- Fast query performance
- Computed once during dbt run

**Cons:**
- Uses storage
- Data can become stale

```sql
{{ config(materialized='table') }}
```

---

### Incremental Materialization

**Pros:**
- Processes only new/changed data
- Balances performance and freshness

**Cons:**
- More complex to set up
- Requires unique key

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id'
    )
}}
```

---

### Ephemeral Materialization

**Pros:**
- No storage required
- Compiled into dependent models

**Cons:**
- Cannot be queried directly
- Can make debugging harder

```sql
{{ config(materialized='ephemeral') }}
```

---

### Choosing the Right Materialization

| Factor | View | Table | Incremental | Ephemeral |
|--------|------|-------|-------------|-----------|
| Data Size | Small | Medium/Large | Large | Small |
| Query Frequency | Low | High | High | N/A |
| Update Frequency | High | Low/Medium | High | N/A |
| Complexity | Low | Medium/High | Medium/High | Low |
| Development Stage | Early | Production | Production | Any |

---

## 3. Deployment and Scheduling

---

### Environment Management

- **Development**: Individual work
- **Testing/Staging**: Integration testing
- **Production**: End-user access

```yaml
# profiles.yml
vyaparbazaar:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: data/vyaparbazaar_dev.duckdb
    staging:
      type: duckdb
      path: data/vyaparbazaar_staging.duckdb
    prod:
      type: duckdb
      path: data/vyaparbazaar_prod.duckdb
```

---

### Version Control

- Use Git for version control
- Create branches for features/fixes
- Use pull requests for code review
- Tag releases with semantic versioning

---

### CI/CD Pipeline

1. Run `dbt compile` to check for syntax errors
2. Run `dbt test` to validate data quality
3. Run `dbt build` in staging
4. Deploy to production after approval

---

### Scheduling Strategies

**Full Refresh vs. Incremental Updates**
- Full Refresh: Rebuild all models from scratch
- Incremental Updates: Update only what's changed

**Dependency-Based Scheduling**
- Schedule based on model dependencies
- Staging → Intermediate → Marts → ML Features

**Business-Driven Scheduling**
- Align with business needs
- Daily reports before business hours
- Real-time dashboards more frequently

---

## 4. Working with Stakeholders

---

### Documentation as Communication

- Write clear model descriptions
- Document business logic in column descriptions
- Use tests to validate business rules
- Share documentation using `dbt docs serve`

---

### Data Contracts

- Define expected data formats
- Document update frequencies
- Specify data quality expectations
- Clarify ownership and responsibilities

---

### Metrics Layer

```yaml
# models/metrics.yml
version: 2

metrics:
  - name: total_revenue
    label: Total Revenue
    model: ref('fct_orders')
    description: "Total revenue from all orders"
    calculation_method: sum
    expression: order_total
    timestamp: order_date
    time_grains: [day, week, month, quarter, year]
    dimensions:
      - customer_state
      - product_category
```

---

### Analytics Development Lifecycle

1. **Requirements gathering**: Understand stakeholder needs
2. **Design**: Plan model structure and tests
3. **Development**: Build and test models
4. **Review**: Peer review and stakeholder feedback
5. **Deployment**: Move to production
6. **Monitoring**: Track usage and performance

---

### Agile Analytics

- Work in short sprints
- Prioritize based on business impact
- Iterate based on feedback
- Demonstrate value early and often

---

## 5. Hands-on Exercises

1. Optimize a Complex Model
2. Implement Incremental Loading
3. Create a Mart Model with Advanced Materializations
4. Develop a Deployment Strategy
5. Stakeholder Documentation

---

## Exercise 5.1: Optimize a Complex Model

**Objective**: Optimize an existing complex model to improve its performance while maintaining the same business logic.

**Key Tasks**:
- Apply early filtering
- Use appropriate join strategies
- Implement efficient aggregations
- Configure appropriate materialization

---

## Exercise 5.2: Implement Incremental Loading

**Objective**: Convert a full-refresh model to an incremental model to improve processing efficiency for large datasets.

**Key Tasks**:
- Implement incremental logic
- Handle potential duplicates
- Configure appropriate parameters
- Add tests for data integrity

---

## Exercise 5.3: Create a Mart Model with Advanced Materializations

**Objective**: Create a business-focused mart model that uses advanced materialization techniques for optimal performance.

**Key Tasks**:
- Combine data from various sources
- Implement appropriate materialization strategies
- Use partitioning and/or clustering
- Add comprehensive documentation and tests

---

## Exercise 5.4: Develop a Deployment Strategy

**Objective**: Design a deployment and scheduling strategy for the VyaparBazaar analytics pipeline.

**Key Tasks**:
- Define environment setup
- Design CI/CD pipeline
- Create scheduling recommendations
- Document monitoring and alerting approach

---

## Exercise 5.5: Stakeholder Documentation

**Objective**: Create comprehensive documentation for business stakeholders to understand and use the analytics models effectively.

**Key Tasks**:
- Document business context and purpose
- Define key metrics
- Create example queries
- Design sample dashboard wireframe

---

## Bonus Exercise: End-to-End Project Optimization

**Objective**: Perform a comprehensive review of the entire VyaparBazaar analytics project and propose optimizations across all layers.

**Key Tasks**:
- Analyze current model performance
- Recommend materialization strategies
- Suggest structural improvements
- Enhance testing and documentation

---

## Additional Resources

- [dbt Best Practices](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [Analytics Engineering Cookbook](https://www.getdbt.com/analytics-engineering/cookbook/)
- [dbt Deployment Guide](https://docs.getdbt.com/docs/deploy/deployment-guides)
- [Locally Optimistic Blog](https://locallyoptimistic.com/)

---

## Next Steps

Congratulations on completing all five modules of the VyaparBazaar Analytics Internship Camp!

You're now ready to apply these skills to the final project, building a comprehensive analytics solution for VyaparBazaar.

---

## Questions?

Thank you for your attention!

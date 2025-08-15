{{
    config(
        materialized='table'
    )
}}

/*
    This model creates features for predicting customer churn.
    
    Churn is defined as customers who haven't placed an order in 90+ days.
    
    The features include:
    - Recency metrics (days since last order, etc.)
    - Frequency metrics (order count, etc.)
    - Monetary metrics (average order value, etc.)
    - Order patterns (weekend shopping, evening shopping, etc.)
    - Product diversity metrics
    - Return and refund behavior
    - Order value trends
    
    These features can be used to train a machine learning model
    to predict which customers are at risk of churning.
*/

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

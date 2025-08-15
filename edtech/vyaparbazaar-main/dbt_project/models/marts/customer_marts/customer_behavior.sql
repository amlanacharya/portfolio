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
        datediff('day', min(order_date), max(order_date)) as customer_lifetime_days,
        datediff('day', max(order_date), current_date) as days_since_last_order
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
        datediff('day', lag(order_date) over (partition by customer_id order by order_date), order_date) as days_between_orders
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
customer_clickstream_base as (
    select
        customer_id,
        device_category,
        count(*) as event_count
    from clickstream
    group by customer_id, device_category
),

customer_device_preference as (
    select
        customer_id,
        device_category as preferred_device
    from (
        select
            customer_id,
            device_category,
            row_number() over (partition by customer_id order by event_count desc) as device_rank
        from customer_clickstream_base
    )
    where device_rank = 1
),

customer_clickstream as (
    select
        c.customer_id,
        count(*) as total_events,
        count(distinct c.session_id) as total_sessions,
        sum(case when c.is_product_view_event then 1 else 0 end) as product_view_count,
        sum(case when c.is_cart_event then 1 else 0 end) as cart_event_count,
        sum(case when c.is_purchase_event then 1 else 0 end) as purchase_event_count,
        count(distinct c.device_category) as device_count,
        cdp.preferred_device
    from clickstream c
    left join customer_device_preference cdp on c.customer_id = cdp.customer_id
    group by c.customer_id, cdp.preferred_device
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

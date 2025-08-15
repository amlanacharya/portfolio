{{
    config(
        materialized='incremental',
        unique_key='customer_id',
        indexes=[
            {'columns': ['customer_id'], 'unique': true}
        ]
    )
}}

/*
    This is an optimized version of the customer behavior model.

    Optimizations include:
    1. Using incremental materialization to process only new data
    2. Pre-aggregating metrics in separate CTEs before joining
    3. Early filtering to reduce data volume
    4. Using COALESCE to handle NULL values properly
    5. Adding appropriate indexes for better query performance

    The model combines customer profile data with aggregated order and clickstream metrics
    to provide a comprehensive view of customer behavior.
*/

-- First, pre-aggregate order metrics to reduce data volume
with order_items_with_totals as (
    select
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp as order_date,
        sum(oi.price + oi.freight_value) as order_total
    from {{ ref('stg_orders') }} o
    join {{ ref('stg_order_items') }} oi on o.order_id = oi.order_id
    group by 1, 2, 3
),

order_metrics as (
    select
        customer_id,
        count(distinct order_id) as order_count,
        sum(order_total) as total_spend,
        avg(order_total) as avg_order_value,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        datediff('day', min(order_date), max(order_date)) as customer_lifetime_days,
        datediff('day', max(order_date), current_date) as days_since_last_order
    from order_items_with_totals

    {% if is_incremental() %}
    -- For incremental runs, only process orders that have been created or updated
    -- since the last time this model was run
    where order_date > (select max(last_order_date) from {{ this }})
    {% endif %}

    group by 1
),

-- Pre-aggregate clickstream metrics to reduce data volume
clickstream_metrics as (
    select
        customer_id,
        count(distinct session_id) as total_sessions,
        count(distinct case when event_type = 'product_view' then event_id else null end) as product_view_count,
        count(distinct case when event_type = 'cart_add' then event_id else null end) as cart_add_count,
        count(distinct case when event_type = 'purchase' then event_id else null end) as purchase_event_count
    from {{ ref('stg_clickstream') }}

    -- Early filtering to reduce data volume
    where customer_id is not null

    {% if is_incremental() %}
    -- For incremental runs, only process events that have occurred
    -- since the last time this model was run
    and event_timestamp > (
        select max(updated_at) from {{ this }}
    )
    {% endif %}

    group by 1
),

-- Calculate purchase frequency for customers with multiple orders
purchase_frequency as (
    select
        customer_id,
        avg(days_between_orders) as avg_days_between_orders
    from (
        select
            customer_id,
            order_id,
            order_date,
            datediff('day',
                lag(order_date) over (partition by customer_id order by order_date),
                order_date
            ) as days_between_orders
        from order_items_with_totals
    ) order_intervals
    where days_between_orders is not null
    group by 1
),

-- Join the pre-aggregated data with customer profiles
final as (
    select
        -- Customer profile
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,

        -- Order metrics with NULL handling
        coalesce(om.order_count, 0) as order_count,
        coalesce(om.total_spend, 0) as total_spend,
        coalesce(om.avg_order_value, 0) as avg_order_value,
        om.first_order_date,
        om.last_order_date,
        coalesce(om.customer_lifetime_days, 0) as customer_lifetime_days,
        coalesce(om.days_since_last_order, 9999) as days_since_last_order,
        coalesce(pf.avg_days_between_orders, 0) as avg_days_between_orders,

        -- Clickstream metrics with NULL handling
        coalesce(cm.total_sessions, 0) as total_sessions,
        coalesce(cm.product_view_count, 0) as product_view_count,
        coalesce(cm.cart_add_count, 0) as cart_add_count,
        coalesce(cm.purchase_event_count, 0) as purchase_event_count,

        -- Derived metrics
        case
            when cm.product_view_count > 0
            then round(cast(cm.purchase_event_count as float) / cast(cm.product_view_count as float), 3)
            else 0
        end as view_to_purchase_ratio,

        -- RFM Segmentation
        case
            when om.days_since_last_order <= 30 then 'Recent'
            when om.days_since_last_order <= 90 then 'Moderate'
            else 'Lapsed'
        end as recency_segment,

        case
            when om.order_count >= 4 then 'High'
            when om.order_count >= 2 then 'Medium'
            when om.order_count = 1 then 'Low'
            else 'None'
        end as frequency_segment,

        case
            when om.total_spend >= 1000 then 'High'
            when om.total_spend >= 500 then 'Medium'
            when om.total_spend > 0 then 'Low'
            else 'None'
        end as monetary_segment,

        -- Metadata for incremental processing
        current_date as updated_at

    from {{ ref('stg_customers') }} c
    left join order_metrics om on c.customer_id = om.customer_id
    left join clickstream_metrics cm on c.customer_id = cm.customer_id
    left join purchase_frequency pf on c.customer_id = pf.customer_id

    {% if is_incremental() %}
    -- For incremental runs, include both new customers and customers with updated metrics
    where c.customer_id not in (select customer_id from {{ this }})
       or c.customer_id in (select customer_id from order_metrics)
       or c.customer_id in (select customer_id from clickstream_metrics)
    {% endif %}
)

select * from final

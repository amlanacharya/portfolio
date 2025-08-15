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
        cast(
            extract(year from o.order_purchase_timestamp) * 10000 +
            extract(month from o.order_purchase_timestamp) * 100 +
            extract(day from o.order_purchase_timestamp)
        as int) as order_date_key,
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

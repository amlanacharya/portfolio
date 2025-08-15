-- models/facts/fct_order_items.sql
{{ config(materialized='table') }}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

sellers as (
    select * from {{ ref('stg_sellers') }}
),

final as (
    select
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        o.customer_id,
        cast(
            extract(year from o.order_purchase_timestamp) * 10000 +
            extract(month from o.order_purchase_timestamp) * 100 +
            extract(day from o.order_purchase_timestamp)
        as int) as order_date_key,
        oi.shipping_limit_date,
        oi.price,
        oi.freight_value,
        (oi.price + oi.freight_value) as total_item_value,
        p.product_category_name,
        s.seller_city,
        s.seller_state,
        -- Add derived fields
        case
            when s.seller_state = c.customer_state then true
            else false
        end as is_same_state_purchase
    from order_items oi
    left join orders o on oi.order_id = o.order_id
    left join customers c on o.customer_id = c.customer_id
    left join products p on oi.product_id = p.product_id
    left join sellers s on oi.seller_id = s.seller_id
)

select * from final

{{
    config(
        materialized='view'
    )
}}

/*
    This is a synthetic refunds model created based on order_items and orders.
    Since there's no actual refunds table in the source data, we're creating one
    by assuming that some orders with specific statuses (canceled, unavailable)
    resulted in refunds, and some random orders also had refunds.
*/

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

-- Generate synthetic refunds based on order status
potential_refunds as (
    select
        o.order_id,
        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        oi.price,
        -- Orders with 'canceled' or 'unavailable' status are more likely to have refunds
        case
            when o.order_status in ('canceled', 'unavailable') then 0.9
            when o.order_status = 'delivered' then 0.05
            else 0.2
        end as refund_probability
    from orders o
    join order_items oi on o.order_id = oi.order_id
),

-- Use a hash function to deterministically select refunds based on probability
refunds as (
    select
        order_id,
        order_item_id,
        product_id,
        seller_id,
        price as refund_amount,
        'refund_' || order_id || '_' || order_item_id as refund_id,
        -- Generate a synthetic refund date (7-14 days after order)
        dateadd('day', 7 + abs(hash(order_id)) % 7, current_date) as refund_date,
        case
            when abs(hash(order_id)) % 100 < 30 then 'damaged_product'
            when abs(hash(order_id)) % 100 < 60 then 'wrong_item'
            when abs(hash(order_id)) % 100 < 80 then 'not_as_described'
            else 'changed_mind'
        end as refund_reason
    from potential_refunds
    where abs(hash(order_id || order_item_id)) % 100 / 100.0 < refund_probability
)

select * from refunds

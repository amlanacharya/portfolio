with orders as (
    select * from {{ ref('stg_orders') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

order_payments as (
    select * from {{ ref('stg_payments') }}
),

order_items_aggregated as (
    select
        order_id,
        count(*) as item_count,
        sum(price) as order_items_value,
        sum(freight_value) as order_freight_value
    from order_items
    group by 1
),

order_payments_aggregated as (
    select
        order_id,
        sum(payment_value) as payment_value,
        array_agg(distinct payment_type) as payment_types,
        max(payment_installments) as max_installments
    from order_payments
    group by 1
),

orders_with_items_and_payments as (
    select
        o.*,
        coalesce(i.item_count, 0) as item_count,
        coalesce(i.order_items_value, 0) as order_items_value,
        coalesce(i.order_freight_value, 0) as order_freight_value,
        coalesce(p.payment_value, 0) as payment_value,
        p.payment_types,
        coalesce(p.max_installments, 0) as max_installments,
        
        -- Calculate delivery times
        case 
            when o.order_delivered_customer_date is not null and o.order_purchase_timestamp is not null
            then date_diff('day', o.order_purchase_timestamp, o.order_delivered_customer_date)
            else null
        end as delivery_time_days,
        
        -- Calculate if delivery was late
        case 
            when o.order_delivered_customer_date is not null and o.order_estimated_delivery_date is not null
            then case 
                when o.order_delivered_customer_date > o.order_estimated_delivery_date then true
                else false
            end
            else null
        end as is_late_delivery,
        
        -- Calculate how many days late
        case 
            when o.order_delivered_customer_date is not null and o.order_estimated_delivery_date is not null
                and o.order_delivered_customer_date > o.order_estimated_delivery_date
            then date_diff('day', o.order_estimated_delivery_date, o.order_delivered_customer_date)
            else 0
        end as days_late
    from orders o
    left join order_items_aggregated i on o.order_id = i.order_id
    left join order_payments_aggregated p on o.order_id = p.order_id
)

select * from orders_with_items_and_payments

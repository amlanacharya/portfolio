with customers as (
    select * from {{ ref('stg_customers') }}
),

orders_with_items as (
    select * from {{ ref('int_orders_with_items') }}
),

customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_zip_code_prefix,
        c.customer_city,
        c.customer_state,
        
        -- Order counts
        count(o.order_id) as order_count,
        sum(case when o.order_status = 'delivered' then 1 else 0 end) as delivered_order_count,
        sum(case when o.order_status = 'canceled' then 1 else 0 end) as canceled_order_count,
        
        -- Order values
        sum(o.order_items_value) as total_order_value,
        sum(o.order_freight_value) as total_freight_value,
        sum(o.payment_value) as total_payment_value,
        
        -- First and last order dates
        min(o.order_purchase_timestamp) as first_order_date,
        max(o.order_purchase_timestamp) as last_order_date,
        
        -- Average order value
        case 
            when count(o.order_id) > 0 
            then sum(o.order_items_value) / count(o.order_id) 
            else 0 
        end as avg_order_value,
        
        -- Late deliveries
        sum(case when o.is_late_delivery = true then 1 else 0 end) as late_delivery_count,
        
        -- Payment methods used
        array_agg(distinct o.payment_types) as payment_methods_used
        
    from customers c
    left join orders_with_items o on c.customer_id = o.customer_id
    group by 1, 2, 3, 4, 5
),

customer_orders_with_metrics as (
    select
        *,
        -- Days since last order
        date_diff('day', last_order_date, current_date) as days_since_last_order,
        
        -- Days between first and last order
        case 
            when first_order_date is not null and last_order_date is not null
            then date_diff('day', first_order_date, last_order_date)
            else 0
        end as days_between_first_last_order,
        
        -- Average order frequency (in days)
        case 
            when order_count > 1 and first_order_date is not null and last_order_date is not null
            then date_diff('day', first_order_date, last_order_date) / (order_count - 1)
            else null
        end as avg_days_between_orders,
        
        -- Customer lifetime value (CLV)
        total_payment_value as customer_lifetime_value,
        
        -- Late delivery rate
        case 
            when delivered_order_count > 0
            then late_delivery_count::float / delivered_order_count
            else 0
        end as late_delivery_rate
    from customer_orders
)

select * from customer_orders_with_metrics

with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('int_orders_with_items') }}
),

support_performance as (
    select * from {{ ref('int_customer_support_performance') }}
),

customer_orders as (
    select
        customer_id,
        count(distinct order_id) as order_count,
        sum(payment_value) as total_spend
    from orders
    group by 1
),

customer_support as (
    select
        customer_id,
        count(*) as ticket_count,
        avg(resolution_time_hours) as avg_resolution_time,
        avg(satisfaction_rating) as avg_satisfaction
    from support_performance
    group by 1
),

final as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        coalesce(co.order_count, 0) as order_count,
        coalesce(co.total_spend, 0) as total_spend,
        coalesce(cs.ticket_count, 0) as ticket_count,
        cs.avg_resolution_time,
        cs.avg_satisfaction,
        case
            when cs.ticket_count = 0 then 'No Support Interaction'
            when cs.avg_satisfaction >= 4 then 'Highly Satisfied'
            when cs.avg_satisfaction >= 3 then 'Satisfied'
            when cs.avg_satisfaction < 3 then 'Dissatisfied'
            else 'Unknown'
        end as satisfaction_segment
    from customers c
    left join customer_orders co on c.customer_id = co.customer_id
    left join customer_support cs on c.customer_id = cs.customer_id
)

select * from final

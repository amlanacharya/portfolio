/*
Sales Overview Mart Model

This model provides a business-focused view of sales data for analytics and reporting.
It aggregates order data by date to create daily sales metrics that can be used by business users.
*/

with orders_with_items as (
    select * from {{ ref('int_orders_with_items') }}
),

-- Extract date parts from orders
orders_with_dates as (
    select
        order_id,
        customer_id,
        order_status,
        order_purchase_timestamp,
        order_items_value,
        order_freight_value,
        payment_value,
        item_count,

        -- Extract date parts
        date_trunc('day', order_purchase_timestamp) as date_day,
        extract(year from order_purchase_timestamp) as year,
        extract(month from order_purchase_timestamp) as month,
        extract(day from order_purchase_timestamp) as day,
        extract(dayofweek from order_purchase_timestamp) as day_of_week,
        case
            when extract(dayofweek from order_purchase_timestamp) in (6, 7) then true
            else false
        end as is_weekend
    from orders_with_items
),

-- Get first order date for each customer to identify new customers
customer_first_orders as (
    select
        customer_id,
        min(order_purchase_timestamp) as first_order_date
    from orders_with_items
    group by 1
),

-- Get top selling products and categories by day
daily_top_products as (
    select
        date_day,

        -- Find top selling category for each day
        (
            select p.product_category_name_english
            from {{ ref('stg_order_items') }} oi
            join {{ ref('stg_products') }} p on oi.product_id = p.product_id
            join orders_with_dates o2 on oi.order_id = o2.order_id
            where o2.date_day = daily_dates.date_day
            group by p.product_category_name_english
            order by count(*) desc
            limit 1
        ) as top_selling_category,

        -- Find top selling product for each day
        (
            select oi.product_id
            from {{ ref('stg_order_items') }} oi
            join orders_with_dates o2 on oi.order_id = o2.order_id
            where o2.date_day = daily_dates.date_day
            group by oi.product_id
            order by count(*) desc
            limit 1
        ) as top_selling_product
    from (
        select distinct date_day
        from orders_with_dates
    ) as daily_dates
),

-- Aggregate sales data by day
daily_sales as (
    select
        date_day,
        year,
        month,
        day,
        day_of_week,
        is_weekend,

        -- Order metrics
        count(order_id) as total_orders,
        sum(item_count) as total_items_sold,
        sum(order_items_value) as total_revenue,
        sum(order_freight_value) as total_freight_value,

        -- Average order value
        case
            when count(order_id) > 0 then sum(order_items_value) / count(order_id)
            else 0
        end as avg_order_value,

        -- Customer metrics
        count(distinct o.customer_id) as unique_customers,

        -- Count new customers (first order on this day)
        sum(
            case
                when o.order_purchase_timestamp = cfo.first_order_date then 1
                else 0
            end
        ) as new_customers,

        -- Order status metrics
        sum(case when order_status = 'canceled' then 1 else 0 end) as canceled_orders
    from orders_with_dates o
    left join customer_first_orders cfo on o.customer_id = cfo.customer_id
    group by 1, 2, 3, 4, 5, 6
),

-- Final sales overview
sales_overview as (
    select
        ds.date_day,
        ds.year,
        ds.month,
        ds.day,
        ds.day_of_week,
        ds.is_weekend,

        -- Order metrics
        ds.total_orders,
        ds.total_items_sold,
        ds.total_revenue,
        ds.total_freight_value,
        ds.avg_order_value,

        -- Customer metrics
        ds.unique_customers,
        ds.new_customers,

        -- Order status metrics
        ds.canceled_orders,

        -- Top selling products and categories
        tp.top_selling_category,
        tp.top_selling_product
    from daily_sales ds
    left join daily_top_products tp on ds.date_day = tp.date_day
)

select * from sales_overview

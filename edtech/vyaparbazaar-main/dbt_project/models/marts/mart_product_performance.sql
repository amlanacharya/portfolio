{{
    config(
        materialized='table',
        partition_by={
            "field": "date_month",
            "data_type": "date",
            "granularity": "month"
        },
        cluster_by=["product_category", "product_id"]
    )
}}

/*
    Product Performance Mart

    This model provides a comprehensive view of product performance including:
    - Sales metrics (units sold, revenue, profit margin)
    - Time-based trends (week-over-week, month-over-month growth)
    - Inventory metrics (stock levels, days of inventory)
    - Customer engagement metrics (view-to-purchase ratio, review score)

    The model is partitioned by month and clustered by product category and ID
    to optimize query performance for common access patterns.
*/

with products as (
    select * from {{ ref('dim_products') }}
),

order_items as (
    select * from {{ ref('fct_order_items') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

inventory as (
    select * from {{ ref('stg_inventory') }}
),

product_reviews as (
    select * from {{ ref('stg_product_reviews') }}
),

clickstream as (
    select *
    from {{ ref('stg_clickstream_incremental') }}
    where event_type = 'product_view'
),

-- Extract date parts for partitioning
order_dates as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        o.order_date,
        date_trunc('month', o.order_date) as date_month,
        date_trunc('week', o.order_date) as date_week
    from order_items oi
    inner join orders o on oi.order_id = o.order_id
),

-- Calculate sales metrics
sales_metrics as (
    select
        od.product_id,
        od.date_month,
        count(distinct od.order_id) as order_count,
        count(od.order_item_id) as units_sold,
        sum(oi.price) as revenue,
        -- Using a 30% margin assumption since cost_price is not available
        sum(oi.price * 0.3) as profit,
        30.0 as profit_margin
    from order_dates od
    inner join order_items oi on od.order_item_id = oi.order_item_id
    group by 1, 2
),

-- Calculate time-based trends
time_trends as (
    select
        sm.product_id,
        sm.date_month,
        sm.revenue,
        sm.units_sold,
        lag(sm.revenue) over (partition by sm.product_id order by sm.date_month) as prev_month_revenue,
        lag(sm.units_sold) over (partition by sm.product_id order by sm.date_month) as prev_month_units,
        case
            when lag(sm.revenue) over (partition by sm.product_id order by sm.date_month) is not null
            then (sm.revenue - lag(sm.revenue) over (partition by sm.product_id order by sm.date_month)) /
                 nullif(lag(sm.revenue) over (partition by sm.product_id order by sm.date_month), 0)
            else null
        end as mom_revenue_growth,
        case
            when lag(sm.units_sold) over (partition by sm.product_id order by sm.date_month) is not null
            then (sm.units_sold - lag(sm.units_sold) over (partition by sm.product_id order by sm.date_month)) /
                 nullif(lag(sm.units_sold) over (partition by sm.product_id order by sm.date_month), 0)
            else null
        end as mom_units_growth
    from sales_metrics sm
),

-- Calculate inventory metrics
inventory_metrics as (
    select
        product_id,
        date_trunc('month', inventory_date) as date_month,
        avg(stock_level) as avg_stock_level,
        min(stock_level) as min_stock_level,
        max(stock_level) as max_stock_level,
        avg(stock_level) / nullif(avg(daily_sales_rate), 0) as avg_days_of_inventory
    from inventory
    group by 1, 2
),

-- Calculate customer engagement metrics
engagement_metrics as (
    select
        pr.product_id,
        date_trunc('month', pr.review_date) as date_month,
        avg(pr.review_score) as avg_review_score,
        count(pr.review_id) as review_count,
        count(distinct cs.customer_id) as view_count,
        count(distinct oi.order_id) as purchase_count,
        count(distinct oi.order_id) / nullif(count(distinct cs.customer_id), 0) as view_to_purchase_ratio
    from products p
    left join product_reviews pr on p.product_id = pr.product_id
    left join clickstream cs on p.product_id = cs.product_id
    left join order_items oi on p.product_id = oi.product_id
    group by 1, 2
),

-- Final product performance model
final as (
    select
        p.product_id,
        -- Using product_id as name since product_name is not available
        p.product_id as product_name,
        p.product_category_name as product_category,
        p.product_category_name_english as product_subcategory,
        tt.date_month,

        -- Sales metrics
        sm.units_sold,
        sm.revenue,
        sm.profit,
        sm.profit_margin,

        -- Time-based trends
        tt.mom_revenue_growth,
        tt.mom_units_growth,

        -- Inventory metrics
        im.avg_stock_level,
        im.min_stock_level,
        im.avg_days_of_inventory,

        -- Customer engagement metrics
        em.avg_review_score,
        em.review_count,
        em.view_to_purchase_ratio,

        -- Ranking metrics
        row_number() over (partition by p.product_category_name, tt.date_month order by sm.revenue desc) as category_revenue_rank,
        row_number() over (partition by tt.date_month order by sm.revenue desc) as overall_revenue_rank,

        -- Seasonal indicators
        case
            when extract(month from tt.date_month) between 9 and 11 then true
            else false
        end as is_festival_season,

        case
            when extract(month from tt.date_month) between 3 and 5 then 'Spring'
            when extract(month from tt.date_month) between 6 and 8 then 'Summer'
            when extract(month from tt.date_month) = 9 then 'Monsoon'
            when extract(month from tt.date_month) between 10 and 11 then 'Autumn'
            else 'Winter'
        end as season
    from products p
    left join sales_metrics sm on p.product_id = sm.product_id
    left join time_trends tt on p.product_id = tt.product_id and sm.date_month = tt.date_month
    left join inventory_metrics im on p.product_id = im.product_id and tt.date_month = im.date_month
    left join engagement_metrics em on p.product_id = em.product_id and tt.date_month = em.date_month
    where tt.date_month is not null
)

select * from final

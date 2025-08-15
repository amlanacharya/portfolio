/*
Product Overview Mart Model

This model provides a business-focused view of product data for analytics and reporting.
It combines data from product orders and other sources to create a comprehensive
product profile that can be used by business users.
*/

with product_orders as (
    select * from {{ ref('int_product_orders') }}
),

-- Get review data for products
product_reviews as (
    select
        oi.product_id,
        count(r.review_id) as review_count,
        avg(r.review_score) as avg_review_score,
        sum(case when r.review_score >= 4 then 1 else 0 end) as positive_reviews,
        sum(case when r.review_score <= 2 then 1 else 0 end) as negative_reviews
    from {{ ref('stg_reviews') }} r
    join {{ ref('stg_orders') }} o on r.order_id = o.order_id
    join {{ ref('stg_order_items') }} oi on o.order_id = oi.order_id
    group by 1
),

-- Final product overview
product_overview as (
    select
        po.product_id,
        po.product_category_name,
        po.product_category_name_english,
        
        -- Order metrics
        po.order_count as total_orders,
        po.item_count as total_units_sold,
        po.total_revenue,
        po.avg_price,
        po.first_order_date,
        po.last_order_date,
        po.days_since_last_order,
        
        -- Customer metrics
        po.customer_count,
        po.avg_revenue_per_customer,
        
        -- Review metrics
        coalesce(pr.review_count, 0) as review_count,
        coalesce(pr.avg_review_score, 0) as avg_review_score,
        coalesce(pr.positive_reviews, 0) as positive_reviews,
        coalesce(pr.negative_reviews, 0) as negative_reviews,
        
        -- Product performance metrics
        case
            when po.order_count > 0 and po.days_since_last_order <= 30 then 'active'
            when po.order_count > 0 and po.days_since_last_order <= 90 then 'slowing'
            when po.order_count > 0 and po.days_since_last_order > 90 then 'inactive'
            else 'never_sold'
        end as product_status,
        
        -- Product performance score (simple version)
        case
            when po.order_count = 0 then 0
            else (
                (coalesce(pr.avg_review_score, 3) / 5 * 0.4) +
                (least(po.order_count / 100, 1) * 0.3) +
                (least(po.total_revenue / 10000, 1) * 0.3)
            ) * 100
        end as performance_score,
        
        -- Product dimensions
        po.product_length_cm,
        po.product_height_cm,
        po.product_width_cm,
        po.product_weight_g,
        po.product_volume_cm3,
        po.product_density,
        
        -- Profitability metrics (placeholder - would need actual cost data)
        po.total_revenue as gross_revenue,
        po.total_freight_value,
        
        -- Seasonality (placeholder - would need time-series analysis)
        'unknown' as seasonality_pattern
    from product_orders po
    left join product_reviews pr on po.product_id = pr.product_id
)

select * from product_overview

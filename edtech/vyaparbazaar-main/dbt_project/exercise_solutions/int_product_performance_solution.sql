/*
Exercise 3.2 Solution: Create a New Intermediate Model

This model calculates various product performance metrics including:
- Product view-to-purchase ratio
- Average review score by product
- Return rate by product
*/

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

reviews as (
    select * from {{ ref('stg_reviews') }}
),

clickstream as (
    select * from {{ ref('stg_clickstream') }}
),

support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

-- Calculate product views from clickstream data
product_views as (
    select
        -- Extract product_id from event_details JSON
        json_extract_string(event_details, '$.product_id') as product_id,
        count(*) as view_count
    from clickstream
    where event_type = 'product_view'
    group by 1
),

-- Calculate product purchases
product_purchases as (
    select
        product_id,
        count(*) as purchase_count,
        sum(price) as total_revenue,
        avg(price) as avg_price
    from order_items
    group by 1
),

-- Calculate product reviews
product_reviews as (
    select
        oi.product_id,
        count(r.review_id) as review_count,
        avg(r.review_score) as avg_review_score,
        sum(case when r.review_score >= 4 then 1 else 0 end) as positive_reviews,
        sum(case when r.review_score <= 2 then 1 else 0 end) as negative_reviews
    from reviews r
    join orders o on r.order_id = o.order_id
    join order_items oi on o.order_id = oi.order_id
    group by 1
),

-- Calculate product returns from support tickets
product_returns as (
    select
        -- Extract product_id from event_details JSON
        json_extract_string(event_details, '$.product_id') as product_id,
        count(*) as return_count
    from support_tickets
    where category = 'return_request'
    group by 1
),

-- Combine all metrics
product_performance as (
    select
        p.product_id,
        p.product_category_name,
        p.product_category_name_english,
        
        -- Basic product info
        p.product_weight_g,
        p.product_length_cm * p.product_width_cm * p.product_height_cm as product_volume_cm3,
        
        -- View metrics
        coalesce(pv.view_count, 0) as view_count,
        
        -- Purchase metrics
        coalesce(pp.purchase_count, 0) as purchase_count,
        coalesce(pp.total_revenue, 0) as total_revenue,
        coalesce(pp.avg_price, 0) as avg_price,
        
        -- Review metrics
        coalesce(pr.review_count, 0) as review_count,
        coalesce(pr.avg_review_score, 0) as avg_review_score,
        coalesce(pr.positive_reviews, 0) as positive_reviews,
        coalesce(pr.negative_reviews, 0) as negative_reviews,
        
        -- Return metrics
        coalesce(ret.return_count, 0) as return_count,
        
        -- Calculated metrics
        case 
            when coalesce(pv.view_count, 0) > 0 
            then coalesce(pp.purchase_count, 0)::float / pv.view_count 
            else 0 
        end as view_to_purchase_ratio,
        
        case 
            when coalesce(pp.purchase_count, 0) > 0 
            then coalesce(ret.return_count, 0)::float / pp.purchase_count 
            else 0 
        end as return_rate,
        
        case 
            when coalesce(pr.review_count, 0) > 0 
            then coalesce(pr.positive_reviews, 0)::float / pr.review_count 
            else 0 
        end as positive_review_ratio,
        
        -- Performance score (weighted average of key metrics)
        case 
            when coalesce(pp.purchase_count, 0) > 0 
            then (
                coalesce(pr.avg_review_score, 0) * 0.4 +
                (1 - case when pp.purchase_count > 0 then coalesce(ret.return_count, 0)::float / pp.purchase_count else 0 end) * 0.4 +
                case when pv.view_count > 0 then coalesce(pp.purchase_count, 0)::float / pv.view_count else 0 end * 0.2
            ) * 100
            else 0
        end as performance_score
        
    from products p
    left join product_views pv on p.product_id = pv.product_id
    left join product_purchases pp on p.product_id = pp.product_id
    left join product_reviews pr on p.product_id = pr.product_id
    left join product_returns ret on p.product_id = ret.product_id
)

select * from product_performance

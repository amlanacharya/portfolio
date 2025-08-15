{{
    config(
        materialized='view'
    )
}}

/*
    Staging model for product reviews
    
    This model standardizes product review data from the raw source,
    including review scores, dates, and product associations.
*/

with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_reviews') }}
),

-- Join with order items to get product_id
order_items as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_order_items') }}
),

reviews_with_products as (
    select
        r.review_id,
        r.order_id,
        oi.product_id,
        r.review_score,
        r.review_comment_title,
        r.review_comment_message,
        r.review_creation_date as review_date,
        r.review_answer_timestamp
    from source r
    left join order_items oi on r.order_id = oi.order_id
)

select * from reviews_with_products

/*
Customer Overview Mart Model

This model provides a business-focused view of customer data for analytics and reporting.
It combines data from customer behavior, orders, and other sources to create a comprehensive
customer profile that can be used by business users.
*/

with customer_behavior as (
    select * from {{ ref('int_customer_behavior') }}
),

customer_orders as (
    select * from {{ ref('int_customer_orders') }}
),

-- Determine customer segments based on RFM (Recency, Frequency, Monetary) analysis
customer_segments as (
    select
        customer_id,

        -- Recency score (1-5)
        case
            when days_since_last_order <= 30 then 5  -- Very recent
            when days_since_last_order <= 60 then 4
            when days_since_last_order <= 90 then 3
            when days_since_last_order <= 180 then 2
            else 1                                   -- Not recent
        end as recency_score,

        -- Frequency score (1-5)
        case
            when order_count >= 10 then 5           -- Very frequent
            when order_count >= 7 then 4
            when order_count >= 5 then 3
            when order_count >= 2 then 2
            else 1                                  -- Infrequent
        end as frequency_score,

        -- Monetary score (1-5)
        case
            when customer_lifetime_value >= 1000 then 5  -- High value
            when customer_lifetime_value >= 750 then 4
            when customer_lifetime_value >= 500 then 3
            when customer_lifetime_value >= 250 then 2
            else 1                                       -- Low value
        end as monetary_score
    from customer_behavior
),

-- Combine segments into a single RFM segment
rfm_segments as (
    select
        customer_id,
        recency_score,
        frequency_score,
        monetary_score,

        -- Combine scores into a single RFM segment
        case
            when (recency_score + frequency_score + monetary_score) >= 13 then 'Champions'
            when (recency_score + frequency_score + monetary_score) >= 10 then 'Loyal Customers'
            when (recency_score >= 4 and (frequency_score + monetary_score) >= 5) then 'Potential Loyalists'
            when (recency_score >= 4 and (frequency_score + monetary_score) < 5) then 'New Customers'
            when (recency_score >= 3 and (frequency_score + monetary_score) >= 5) then 'Need Attention'
            when (recency_score < 3 and (frequency_score + monetary_score) >= 5) then 'At Risk'
            when (recency_score < 2 and frequency_score < 2 and monetary_score >= 4) then 'Cannot Lose Them'
            when (recency_score < 2 and frequency_score >= 3 and monetary_score < 3) then 'About to Sleep'
            when (recency_score < 2 and frequency_score < 2 and monetary_score < 2) then 'Hibernating'
            else 'Others'
        end as customer_segment,

        -- Value tier based on monetary score
        case
            when monetary_score >= 4 then 'high'
            when monetary_score = 3 then 'medium'
            else 'low'
        end as customer_value_tier
    from customer_segments
),

-- Final customer overview
customer_overview as (
    select
        cb.customer_id,
        cb.customer_unique_id,
        cb.customer_city,
        cb.customer_state,

        -- Customer segmentation
        rfm.customer_segment,
        rfm.customer_value_tier,

        -- Order metrics
        cb.first_order_date,
        cb.last_order_date,
        cb.days_since_last_order,
        cb.order_count as lifetime_orders,
        cb.customer_lifetime_value as lifetime_value,
        cb.avg_order_value,

        -- Determine preferred category based on order history
        -- This would typically come from a more complex analysis
        -- For now, we'll use a placeholder
        'placeholder' as preferred_category,

        -- Determine preferred payment method
        -- This would typically come from a more complex analysis
        -- For now, we'll use a placeholder
        'placeholder' as preferred_payment_method,

        -- Customer satisfaction
        cb.avg_review_score as satisfaction_score,

        -- Activity flag
        case
            when cb.days_since_last_order <= 90 then true
            else false
        end as is_active,

        -- Churn risk (simple model based on recency and satisfaction)
        case
            when cb.days_since_last_order > 60 and (cb.avg_review_score < 3 or cb.avg_review_score is null) then 'high'
            when cb.days_since_last_order > 30 and cb.avg_review_score < 4 then 'medium'
            when cb.days_since_last_order > 90 then 'medium'
            else 'low'
        end as churn_risk,

        -- Engagement metrics
        cb.total_events,
        cb.total_app_events,
        cb.cart_to_order_conversion_rate,

        -- Support and review metrics
        cb.total_tickets,
        cb.avg_satisfaction_rating,
        cb.total_reviews,

        -- Channel preference
        cb.preferred_device as preferred_channel
    from customer_behavior cb
    left join rfm_segments rfm on cb.customer_id = rfm.customer_id
)

select * from customer_overview

with customer_behavior as (
    select * from {{ ref('int_customer_behavior') }}
),

customer_segmentation_features as (
    select
        customer_id,
        customer_unique_id,
        customer_city,
        customer_state,
        
        -- RFM features
        days_since_last_order as recency_days,
        order_count as frequency,
        avg_order_value as monetary_value,
        
        -- Engagement level
        case
            when total_events > 100 and total_app_events > 50 then 'high'
            when total_events > 50 and total_app_events > 20 then 'medium'
            when total_events > 0 or total_app_events > 0 then 'low'
            else 'none'
        end as engagement_level,
        
        -- Channel preference
        case
            when total_app_events > total_events - total_app_events then 'app'
            when total_events - total_app_events > total_app_events then 'web'
            when total_app_events > 0 and total_events - total_app_events > 0 then 'omnichannel'
            else 'unknown'
        end as channel_preference,
        
        -- Device preference
        preferred_device,
        
        -- Purchase behavior
        case
            when avg_order_value > 5000 then 'high_value'
            when avg_order_value > 2000 then 'medium_value'
            else 'low_value'
        end as purchase_value_segment,
        
        case
            when order_count > 5 then 'frequent'
            when order_count > 2 then 'regular'
            else 'occasional'
        end as purchase_frequency_segment,
        
        -- Loyalty indicators
        case
            when days_since_last_order <= 30 and order_count >= 3 then 'loyal'
            when days_since_last_order <= 90 and order_count >= 2 then 'potential_loyal'
            when days_since_last_order > 90 and order_count >= 2 then 'churned_loyal'
            when days_since_last_order <= 90 and order_count = 1 then 'new_customer'
            else 'churned_new'
        end as loyalty_segment,
        
        -- Satisfaction indicators
        case
            when avg_review_score >= 4 then 'highly_satisfied'
            when avg_review_score >= 3 then 'satisfied'
            when avg_review_score > 0 then 'unsatisfied'
            else 'unknown'
        end as satisfaction_segment,
        
        -- Support needs
        case
            when total_tickets = 0 then 'self_sufficient'
            when total_tickets > 3 then 'high_support'
            else 'normal_support'
        end as support_segment,
        
        -- Raw metrics for clustering
        order_count,
        total_order_value,
        avg_order_value,
        days_since_last_order,
        total_events,
        total_app_events,
        cart_to_order_conversion_rate,
        avg_review_score,
        total_tickets
    from customer_behavior
)

select * from customer_segmentation_features

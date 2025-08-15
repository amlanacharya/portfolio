with customer_behavior as (
    select * from {{ ref('int_customer_behavior') }}
),

customer_ltv_features as (
    select
        customer_id,
        customer_unique_id,
        customer_city,
        customer_state,
        
        -- Current LTV
        customer_lifetime_value as current_ltv,
        
        -- Recency, Frequency, Monetary
        days_since_last_order as recency,
        order_count as frequency,
        avg_order_value as monetary,
        
        -- Order patterns
        order_count,
        delivered_order_count,
        canceled_order_count,
        canceled_order_count::float / nullif(order_count, 0) as cancel_rate,
        
        -- Time as customer (days)
        date_diff('day', first_order_date, current_date) as days_as_customer,
        
        -- Order frequency (orders per month)
        case 
            when date_diff('day', first_order_date, current_date) > 0
            then order_count::float / (date_diff('day', first_order_date, current_date) / 30.0)
            else 0
        end as orders_per_month,
        
        -- Average order value trend (if multiple orders)
        case 
            when order_count >= 2 then
                case 
                    when avg_order_value > total_order_value / order_count then 'increasing'
                    when avg_order_value < total_order_value / order_count then 'decreasing'
                    else 'stable'
                end
            else 'insufficient_data'
        end as aov_trend,
        
        -- Engagement metrics
        total_events,
        total_sessions,
        active_days,
        page_view_count,
        product_view_count,
        add_to_cart_count,
        
        -- App engagement
        total_app_events,
        total_app_sessions,
        app_active_days,
        total_app_time_seconds,
        
        -- Conversion metrics
        cart_to_order_conversion_rate,
        view_to_cart_conversion_rate,
        
        -- Support and satisfaction
        total_tickets,
        avg_satisfaction_rating,
        
        -- Review behavior
        avg_review_score,
        positive_reviews,
        negative_reviews,
        
        -- Device and platform preferences
        preferred_device,
        preferred_os,
        
        -- Geographic features
        customer_city,
        customer_state
    from customer_behavior
    where order_count > 0  -- Only include customers who have made at least one order
)

select * from customer_ltv_features

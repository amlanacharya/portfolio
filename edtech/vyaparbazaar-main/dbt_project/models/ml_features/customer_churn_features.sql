with customer_behavior as (
    select * from {{ ref('int_customer_behavior') }}
),

customer_churn_features as (
    select
        customer_id,
        customer_unique_id,
        customer_city,
        customer_state,
        
        -- Define churn (customers who haven't ordered in 90+ days)
        case 
            when days_since_last_order > 90 then 1
            else 0
        end as is_churned,
        
        -- Recency
        days_since_last_order,
        
        -- Frequency
        order_count,
        
        -- Monetary
        total_order_value,
        avg_order_value,
        customer_lifetime_value,
        
        -- Order patterns
        canceled_order_count,
        canceled_order_count::float / nullif(order_count, 0) as cancel_rate,
        
        -- Engagement metrics
        total_events,
        total_sessions,
        active_days,
        page_view_count,
        product_view_count,
        add_to_cart_count,
        search_count,
        
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
        high_priority_tickets,
        avg_satisfaction_rating,
        
        -- Review behavior
        total_reviews,
        avg_review_score,
        positive_reviews,
        negative_reviews,
        
        -- Device and platform preferences
        preferred_device,
        preferred_os,
        
        -- Time as customer (days)
        date_diff('day', first_order_date, current_date) as days_as_customer,
        
        -- Order frequency (orders per month)
        case 
            when date_diff('day', first_order_date, current_date) > 0
            then order_count::float / (date_diff('day', first_order_date, current_date) / 30.0)
            else 0
        end as orders_per_month
    from customer_behavior
    where order_count > 0  -- Only include customers who have made at least one order
)

select * from customer_churn_features

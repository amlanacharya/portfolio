with customer_orders as (
    select * from {{ ref('int_customer_orders') }}
),

clickstream as (
    select * from {{ ref('stg_clickstream') }}
),

app_usage as (
    select * from {{ ref('stg_app_usage') }}
),

support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

reviews as (
    select * from {{ ref('stg_reviews') }}
),

-- Aggregate clickstream data by customer
customer_clickstream as (
    select
        customer_id,
        count(*) as total_events,
        count(distinct session_id) as total_sessions,
        count(distinct date_trunc('day', event_timestamp)) as active_days,
        
        -- Event type counts
        sum(case when event_type = 'page_view' then 1 else 0 end) as page_view_count,
        sum(case when event_type = 'product_view' then 1 else 0 end) as product_view_count,
        sum(case when event_type = 'add_to_cart' then 1 else 0 end) as add_to_cart_count,
        sum(case when event_type = 'purchase' then 1 else 0 end) as purchase_event_count,
        sum(case when event_type = 'search' then 1 else 0 end) as search_count,
        
        -- Device usage
        sum(case when device = 'desktop' then 1 else 0 end) as desktop_events,
        sum(case when device = 'mobile_app' then 1 else 0 end) as mobile_app_events,
        sum(case when device = 'mobile_web' then 1 else 0 end) as mobile_web_events,
        sum(case when device = 'tablet' then 1 else 0 end) as tablet_events,
        
        -- Time metrics
        min(event_timestamp) as first_event_date,
        max(event_timestamp) as last_event_date
    from clickstream
    group by 1
),

-- Aggregate app usage data by customer
customer_app_usage as (
    select
        customer_id,
        count(*) as total_app_events,
        count(distinct session_id) as total_app_sessions,
        count(distinct date_trunc('day', event_timestamp)) as app_active_days,
        
        -- Screen views
        sum(case when screen = 'home' then 1 else 0 end) as home_screen_views,
        sum(case when screen = 'product_detail' then 1 else 0 end) as product_detail_views,
        sum(case when screen = 'cart' then 1 else 0 end) as cart_views,
        
        -- Actions
        sum(case when action = 'add_to_cart' then 1 else 0 end) as app_add_to_cart_count,
        sum(case when action = 'purchase' then 1 else 0 end) as app_purchase_count,
        
        -- OS usage
        sum(case when operating_system = 'Android' then 1 else 0 end) as android_events,
        sum(case when operating_system = 'iOS' then 1 else 0 end) as ios_events,
        
        -- Time spent
        sum(duration_seconds) as total_app_time_seconds,
        
        -- Time metrics
        min(event_timestamp) as first_app_event_date,
        max(event_timestamp) as last_app_event_date
    from app_usage
    group by 1
),

-- Aggregate support ticket data by customer
customer_support as (
    select
        customer_id,
        count(*) as total_tickets,
        
        -- Ticket categories
        sum(case when category = 'order_status' then 1 else 0 end) as order_status_tickets,
        sum(case when category = 'return_request' then 1 else 0 end) as return_request_tickets,
        sum(case when category = 'refund_status' then 1 else 0 end) as refund_status_tickets,
        sum(case when category = 'product_inquiry' then 1 else 0 end) as product_inquiry_tickets,
        sum(case when category = 'payment_issue' then 1 else 0 end) as payment_issue_tickets,
        sum(case when category = 'delivery_delay' then 1 else 0 end) as delivery_delay_tickets,
        sum(case when category = 'damaged_product' then 1 else 0 end) as damaged_product_tickets,
        
        -- Ticket status
        sum(case when status = 'resolved' or status = 'closed' then 1 else 0 end) as resolved_tickets,
        sum(case when status = 'open' or status = 'in_progress' or status = 'escalated' then 1 else 0 end) as open_tickets,
        
        -- Satisfaction metrics
        avg(satisfaction_rating) as avg_satisfaction_rating,
        
        -- Priority metrics
        sum(case when priority = 'high' or priority = 'urgent' then 1 else 0 end) as high_priority_tickets
    from support_tickets
    group by 1
),

-- Aggregate review data by customer
customer_reviews as (
    select
        o.customer_id,
        count(r.review_id) as total_reviews,
        avg(r.review_score) as avg_review_score,
        sum(case when r.review_score >= 4 then 1 else 0 end) as positive_reviews,
        sum(case when r.review_score <= 2 then 1 else 0 end) as negative_reviews
    from reviews r
    join {{ ref('stg_orders') }} o on r.order_id = o.order_id
    group by 1
),

-- Combine all customer behavior data
customer_behavior as (
    select
        co.customer_id,
        co.customer_unique_id,
        co.customer_city,
        co.customer_state,
        
        -- Order metrics
        co.order_count,
        co.delivered_order_count,
        co.canceled_order_count,
        co.total_order_value,
        co.avg_order_value,
        co.first_order_date,
        co.last_order_date,
        co.days_since_last_order,
        co.customer_lifetime_value,
        
        -- Clickstream metrics
        coalesce(cs.total_events, 0) as total_events,
        coalesce(cs.total_sessions, 0) as total_sessions,
        coalesce(cs.active_days, 0) as active_days,
        coalesce(cs.page_view_count, 0) as page_view_count,
        coalesce(cs.product_view_count, 0) as product_view_count,
        coalesce(cs.add_to_cart_count, 0) as add_to_cart_count,
        coalesce(cs.purchase_event_count, 0) as purchase_event_count,
        coalesce(cs.search_count, 0) as search_count,
        
        -- Device preference
        case
            when coalesce(cs.total_events, 0) > 0 then
                case
                    when cs.desktop_events > cs.mobile_app_events and cs.desktop_events > cs.mobile_web_events and cs.desktop_events > cs.tablet_events then 'desktop'
                    when cs.mobile_app_events > cs.desktop_events and cs.mobile_app_events > cs.mobile_web_events and cs.mobile_app_events > cs.tablet_events then 'mobile_app'
                    when cs.mobile_web_events > cs.desktop_events and cs.mobile_web_events > cs.mobile_app_events and cs.mobile_web_events > cs.tablet_events then 'mobile_web'
                    when cs.tablet_events > cs.desktop_events and cs.tablet_events > cs.mobile_app_events and cs.tablet_events > cs.mobile_web_events then 'tablet'
                    else 'mixed'
                end
            else 'unknown'
        end as preferred_device,
        
        -- App usage metrics
        coalesce(au.total_app_events, 0) as total_app_events,
        coalesce(au.total_app_sessions, 0) as total_app_sessions,
        coalesce(au.app_active_days, 0) as app_active_days,
        coalesce(au.total_app_time_seconds, 0) as total_app_time_seconds,
        
        -- OS preference
        case
            when coalesce(au.total_app_events, 0) > 0 then
                case
                    when au.android_events > au.ios_events then 'Android'
                    when au.ios_events > au.android_events then 'iOS'
                    else 'mixed'
                end
            else 'unknown'
        end as preferred_os,
        
        -- Support metrics
        coalesce(st.total_tickets, 0) as total_tickets,
        coalesce(st.resolved_tickets, 0) as resolved_tickets,
        coalesce(st.open_tickets, 0) as open_tickets,
        coalesce(st.avg_satisfaction_rating, 0) as avg_satisfaction_rating,
        coalesce(st.high_priority_tickets, 0) as high_priority_tickets,
        
        -- Review metrics
        coalesce(rv.total_reviews, 0) as total_reviews,
        coalesce(rv.avg_review_score, 0) as avg_review_score,
        coalesce(rv.positive_reviews, 0) as positive_reviews,
        coalesce(rv.negative_reviews, 0) as negative_reviews,
        
        -- Conversion metrics
        case 
            when coalesce(cs.add_to_cart_count, 0) > 0 
            then co.order_count::float / cs.add_to_cart_count 
            else 0 
        end as cart_to_order_conversion_rate,
        
        case 
            when coalesce(cs.product_view_count, 0) > 0 
            then cs.add_to_cart_count::float / cs.product_view_count 
            else 0 
        end as view_to_cart_conversion_rate
        
    from customer_orders co
    left join customer_clickstream cs on co.customer_unique_id = cs.customer_id
    left join customer_app_usage au on co.customer_unique_id = au.customer_id
    left join customer_support st on co.customer_unique_id = st.customer_id
    left join customer_reviews rv on co.customer_id = rv.customer_id
)

select * from customer_behavior

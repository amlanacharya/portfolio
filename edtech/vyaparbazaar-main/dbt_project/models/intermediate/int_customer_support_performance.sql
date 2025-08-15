with support_tickets as (
    select * from {{ ref('stg_support_tickets') }}
),

ticket_metrics as (
    select
        ticket_id,
        customer_id,
        category,
        created_at,
        resolved_at,
        -- Fixed the macro call to use a string literal for the unit parameter
        {{ calculate_resolution_time('created_at', 'resolved_at', "'hour'") }} as resolution_time_hours,
        satisfaction_rating
    from support_tickets
),

ticket_categories as (
    select
        ticket_id,
        customer_id,
        category,
        resolution_time_hours,
        {{ categorize_resolution_time('resolution_time_hours') }} as resolution_time_category,
        satisfaction_rating,
        {{ calculate_satisfaction_score('satisfaction_rating') }} as satisfaction_score
    from ticket_metrics
)

select * from ticket_categories

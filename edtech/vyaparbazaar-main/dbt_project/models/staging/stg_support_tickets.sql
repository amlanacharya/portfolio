with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_support_tickets') }}
),

renamed as (
    select
        ticket_id,
        customer_id,
        order_id,
        cast(created_at as timestamp) as created_at,
        category,
        channel,
        status,
        cast(resolved_at as timestamp) as resolved_at,
        satisfaction_rating,
        priority
    from source
)

select * from renamed

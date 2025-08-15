with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_app_usage') }}
),

renamed as (
    select
        event_id,
        customer_id,
        cast(event_timestamp as timestamp) as event_timestamp,
        screen,
        action,
        operating_system,
        app_version,
        session_id,
        duration_seconds,
        device_model
    from source
)

select * from renamed

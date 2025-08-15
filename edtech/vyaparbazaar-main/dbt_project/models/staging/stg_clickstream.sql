with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_clickstream') }}
),

renamed as (
    select
        event_id,
        customer_id,
        cast(event_timestamp as timestamp) as event_timestamp,
        event_type,
        page_type,
        device,
        browser,
        operating_system,
        app_version,
        session_id,
        event_details
    from source
)

select * from renamed

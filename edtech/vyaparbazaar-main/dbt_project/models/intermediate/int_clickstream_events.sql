{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

with source as (
    select * from {{ ref('stg_clickstream') }}
    {% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
    {% endif %}
),

transformed as (
    select
        event_id,
        customer_id,
        -- Using strftime instead of date_format (which is not available in DuckDB)
        cast(strftime(event_timestamp, '%Y%m%d') as int) as event_date_key,
        event_timestamp,
        event_type,
        page_type,
        -- Derive device category
        case
            when lower(device) like '%mobile%' or lower(device) like '%phone%' then 'Mobile'
            when lower(device) like '%tablet%' or lower(device) like '%ipad%' then 'Tablet'
            else 'Desktop'
        end as device_category,
        -- Derive browser category
        case
            when lower(browser) like '%chrome%' then 'Chrome'
            when lower(browser) like '%firefox%' then 'Firefox'
            when lower(browser) like '%safari%' then 'Safari'
            when lower(browser) like '%edge%' then 'Edge'
            when lower(browser) like '%opera%' then 'Opera'
            else 'Other'
        end as browser_category,
        session_id,
        -- Event type flags
        case when lower(event_type) like '%purchase%' then true else false end as is_purchase_event,
        case when lower(event_type) like '%cart%' then true else false end as is_cart_event,
        case when lower(event_type) like '%product%' and lower(event_type) like '%view%' then true else false end as is_product_view_event
    from source
)

select * from transformed

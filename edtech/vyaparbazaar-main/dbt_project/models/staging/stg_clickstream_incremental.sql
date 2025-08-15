{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='delete+insert'
    )
}}

/*
    This is an incremental version of the clickstream staging model.

    Benefits of incremental processing:
    1. Processes only new data since the last run
    2. Significantly reduces processing time for large datasets
    3. Enables more frequent updates
    4. Reduces resource usage

    The delete+insert strategy is used to handle potential duplicates
    or updates to existing events.
*/

with source as (
    select
        event_id,
        customer_id,
        event_timestamp,
        event_type,
        page_type,
        device,
        browser,
        session_id,
        -- product_id is not available in the source table
        -- Using NULL as a placeholder
        NULL as product_id,
        -- referrer, user_agent, and ip_address are not available in the source table
        -- Using NULL as placeholders
        NULL as referrer,
        NULL as user_agent,
        NULL as ip_address
    from {{ source('vyaparbazaar_raw', 'vyaparbazaar_clickstream') }}

    {% if is_incremental() %}
    -- Only process events that occurred after the most recent event in the existing table
    -- Add a small buffer (1 hour) to catch any late-arriving events with timestamps
    -- that might fall within the already processed time range
    where event_timestamp > (select max(event_timestamp) - interval '1 hour' from {{ this }})
    {% endif %}
),

-- Add data quality checks and transformations
transformed as (
    select
        event_id,
        customer_id,
        cast(event_timestamp as timestamp) as event_timestamp,

        -- Standardize event types
        case
            when lower(event_type) like '%view%' and lower(event_type) like '%product%' then 'product_view'
            when lower(event_type) like '%add%' and lower(event_type) like '%cart%' then 'cart_add'
            when lower(event_type) like '%remove%' and lower(event_type) like '%cart%' then 'cart_remove'
            when lower(event_type) like '%checkout%' then 'checkout'
            when lower(event_type) like '%purchase%' then 'purchase'
            when lower(event_type) like '%search%' then 'search'
            when lower(event_type) like '%login%' then 'login'
            when lower(event_type) like '%signup%' then 'signup'
            else lower(event_type)
        end as event_type,

        -- Standardize page types
        case
            when lower(page_type) like '%home%' then 'home'
            when lower(page_type) like '%product%' and lower(page_type) like '%list%' then 'product_list'
            when lower(page_type) like '%product%' and lower(page_type) like '%detail%' then 'product_detail'
            when lower(page_type) like '%cart%' then 'cart'
            when lower(page_type) like '%checkout%' then 'checkout'
            when lower(page_type) like '%account%' then 'account'
            when lower(page_type) like '%order%' and lower(page_type) like '%confirm%' then 'order_confirmation'
            when lower(page_type) like '%search%' then 'search_results'
            else lower(page_type)
        end as page_type,

        -- Standardize device categories
        case
            when lower(device) like '%mobile%' or lower(device) like '%phone%' or lower(device) like '%android%' or lower(device) like '%iphone%' then 'mobile'
            when lower(device) like '%tablet%' or lower(device) like '%ipad%' then 'tablet'
            else 'desktop'
        end as device_category,

        device,

        -- Standardize browser categories
        case
            when lower(browser) like '%chrome%' then 'chrome'
            when lower(browser) like '%firefox%' then 'firefox'
            when lower(browser) like '%safari%' then 'safari'
            when lower(browser) like '%edge%' then 'edge'
            when lower(browser) like '%opera%' then 'opera'
            when lower(browser) like '%ie%' or lower(browser) like '%internet explorer%' then 'ie'
            else 'other'
        end as browser_category,

        browser,
        session_id,
        product_id,
        referrer,

        -- Extract referrer type
        case
            when referrer is null then 'direct'
            when lower(referrer) like '%google%' then 'search'
            when lower(referrer) like '%bing%' then 'search'
            when lower(referrer) like '%yahoo%' then 'search'
            when lower(referrer) like '%facebook%' then 'social'
            when lower(referrer) like '%instagram%' then 'social'
            when lower(referrer) like '%twitter%' then 'social'
            when lower(referrer) like '%linkedin%' then 'social'
            when lower(referrer) like '%email%' then 'email'
            when lower(referrer) like '%newsletter%' then 'email'
            else 'other'
        end as referrer_type,

        -- Add metadata for tracking incremental loads
        current_date as _etl_loaded_at
    from source
    where event_id is not null  -- Ensure we have a valid primary key
)

select * from transformed

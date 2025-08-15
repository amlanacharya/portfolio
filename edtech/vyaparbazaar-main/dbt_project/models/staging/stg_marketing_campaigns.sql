with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_marketing_campaigns') }}
),

renamed as (
    select
        campaign_id,
        campaign_name,
        channel,
        campaign_type,
        cast(start_date as date) as start_date,
        cast(end_date as date) as end_date,
        budget,
        impressions,
        clicks,
        conversions,
        revenue,
        target_audience,
        discount_percentage
    from source
)

select * from renamed

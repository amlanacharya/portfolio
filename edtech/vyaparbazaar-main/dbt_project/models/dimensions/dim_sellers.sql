-- models/dimensions/dim_sellers.sql
{{ config(materialized='table') }}

with sellers as (
    select * from {{ ref('stg_sellers') }}
),

final as (
    select
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state,
        -- Add derived fields
        case
            when seller_state in ('SP', 'RJ', 'MG', 'ES') then 'Southeast'
            when seller_state in ('PR', 'SC', 'RS') then 'South'
            when seller_state in ('DF', 'GO', 'MT', 'MS') then 'Central-West'
            when seller_state in ('BA', 'SE', 'AL', 'PE', 'PB', 'RN', 'CE', 'PI', 'MA') then 'Northeast'
            when seller_state in ('TO', 'PA', 'AM', 'RO', 'AC', 'RR', 'AP') then 'North'
            else 'Unknown'
        end as region,
        current_timestamp as valid_from,
        null as valid_to,
        true as is_current
    from sellers
)

select * from final

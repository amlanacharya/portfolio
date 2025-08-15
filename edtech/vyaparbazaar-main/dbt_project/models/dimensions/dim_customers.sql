-- models/dimensions/dim_customers.sql
{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('stg_customers') }}
),

final as (
    select
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state,
        -- Add derived fields
        case
            when customer_state in ('SP', 'RJ', 'MG', 'ES') then 'Southeast'
            when customer_state in ('PR', 'SC', 'RS') then 'South'
            when customer_state in ('DF', 'GO', 'MT', 'MS') then 'Central-West'
            when customer_state in ('BA', 'SE', 'AL', 'PE', 'PB', 'RN', 'CE', 'PI', 'MA') then 'Northeast'
            when customer_state in ('TO', 'PA', 'AM', 'RO', 'AC', 'RR', 'AP') then 'North'
            else 'Unknown'
        end as region,
        current_timestamp as valid_from,
        null as valid_to,
        true as is_current
    from customers
)

select * from final

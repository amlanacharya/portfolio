-- models/dimensions/dim_products.sql
{{ config(materialized='table') }}

with products as (
    select * from {{ ref('stg_products') }}
),

final as (
    select
        product_id,
        product_category_name,
        product_category_name_english,
        product_weight_g,
        product_length_cm,
        product_height_cm,
        product_width_cm,
        -- Add derived fields
        case
            when product_weight_g < 500 then 'Light'
            when product_weight_g < 2000 then 'Medium'
            when product_weight_g < 10000 then 'Heavy'
            else 'Very Heavy'
        end as weight_category,

        -- Calculate volume in cubic cm
        (product_length_cm * product_height_cm * product_width_cm) as volume_cm3,

        -- Categorize by size
        case
            when (product_length_cm * product_height_cm * product_width_cm) < 1000 then 'Small'
            when (product_length_cm * product_height_cm * product_width_cm) < 8000 then 'Medium'
            when (product_length_cm * product_height_cm * product_width_cm) < 27000 then 'Large'
            else 'Extra Large'
        end as size_category,

        current_timestamp as valid_from,
        null as valid_to,
        true as is_current
    from products
)

select * from final

with source as (
    select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_products') }}
),

renamed as (
    select
        product_id,
        product_category_name,
        product_category_name_english,
        product_length_cm,
        product_height_cm,
        product_width_cm,
        product_weight_g
    from source
)

select * from renamed

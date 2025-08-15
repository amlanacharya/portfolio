{{
    config(
        materialized='view'
    )
}}

/*
    Staging model for inventory data

    This model standardizes inventory data from the raw source,
    including stock levels, inventory dates, and daily sales rates.
*/

-- Note: The raw_inventory table doesn't exist yet
-- Creating a mock inventory table for development purposes
with source as (
    -- Using a CTE to create mock inventory data
    -- This will be replaced with actual data when available
    select
        cast(p.product_id as varchar) || '-INV' as inventory_id,
        p.product_id,
        current_date() as inventory_date,
        cast(random() * 100 as integer) as stock_level,
        20 as reorder_level,
        50 as reorder_quantity,
        cast(random() * 5 as decimal(10,2)) as daily_sales_rate,
        'WH' || cast(cast(random() * 3 as integer) + 1 as varchar) as warehouse_id,
        current_date as last_updated_at
    from {{ source('vyaparbazaar_raw', 'vyaparbazaar_products') }} p
),

renamed as (
    select
        inventory_id,
        product_id,
        inventory_date,
        stock_level,
        reorder_level,
        reorder_quantity,
        daily_sales_rate,
        warehouse_id,
        last_updated_at
    from source
)

select * from renamed

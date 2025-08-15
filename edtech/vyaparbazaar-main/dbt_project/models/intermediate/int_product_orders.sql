with products as (
    select * from {{ ref('stg_products') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

product_orders as (
    select
        p.product_id,
        p.product_category_name,
        p.product_category_name_english,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm,
        p.product_weight_g,
        
        -- Order counts
        count(distinct oi.order_id) as order_count,
        count(oi.order_item_id) as item_count,
        
        -- Order values
        sum(oi.price) as total_revenue,
        sum(oi.freight_value) as total_freight_value,
        
        -- First and last order dates
        min(o.order_purchase_timestamp) as first_order_date,
        max(o.order_purchase_timestamp) as last_order_date,
        
        -- Average price
        avg(oi.price) as avg_price,
        
        -- Count of unique customers
        count(distinct o.customer_id) as customer_count
        
    from products p
    left join order_items oi on p.product_id = oi.product_id
    left join orders o on oi.order_id = o.order_id
    group by 1, 2, 3, 4, 5, 6, 7
),

product_orders_with_metrics as (
    select
        *,
        -- Days since last order
        date_diff('day', last_order_date, current_date) as days_since_last_order,
        
        -- Average revenue per order
        case 
            when order_count > 0 
            then total_revenue / order_count 
            else 0 
        end as avg_revenue_per_order,
        
        -- Average items per order
        case 
            when order_count > 0 
            then item_count::float / order_count 
            else 0 
        end as avg_items_per_order,
        
        -- Average revenue per customer
        case 
            when customer_count > 0 
            then total_revenue / customer_count 
            else 0 
        end as avg_revenue_per_customer,
        
        -- Product volume in cubic cm
        product_length_cm * product_height_cm * product_width_cm as product_volume_cm3,
        
        -- Product density (g/cm³)
        case 
            when (product_length_cm * product_height_cm * product_width_cm) > 0 
            then product_weight_g / (product_length_cm * product_height_cm * product_width_cm)
            else null
        end as product_density
    from product_orders
)

select * from product_orders_with_metrics

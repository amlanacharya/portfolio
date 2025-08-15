with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

-- Get all customer-product interactions
customer_product_interactions as (
    select
        o.customer_id,
        oi.product_id,
        p.product_category_name,
        p.product_category_name_english,
        count(*) as purchase_count,
        sum(oi.price) as total_spent,
        min(o.order_purchase_timestamp) as first_purchase_date,
        max(o.order_purchase_timestamp) as last_purchase_date
    from order_items oi
    join orders o on oi.order_id = o.order_id
    join products p on oi.product_id = p.product_id
    group by 1, 2, 3, 4
),

-- Get customer category preferences
customer_category_preferences as (
    select
        customer_id,
        product_category_name_english,
        count(*) as category_purchase_count,
        sum(total_spent) as category_total_spent
    from customer_product_interactions
    group by 1, 2
),

-- Rank categories by customer preference
customer_category_ranks as (
    select
        customer_id,
        product_category_name_english,
        category_purchase_count,
        category_total_spent,
        row_number() over (partition by customer_id order by category_purchase_count desc, category_total_spent desc) as category_rank
    from customer_category_preferences
),

-- Get product co-purchase patterns
product_copurchases as (
    select
        oi1.product_id as product_id_1,
        oi2.product_id as product_id_2,
        count(distinct oi1.order_id) as copurchase_count
    from order_items oi1
    join order_items oi2 on oi1.order_id = oi2.order_id and oi1.product_id < oi2.product_id
    group by 1, 2
),

-- Create recommendation features
recommendation_features as (
    select
        cpi.customer_id,
        cpi.product_id,
        cpi.product_category_name_english,
        cpi.purchase_count,
        cpi.total_spent,
        
        -- Recency feature (days since last purchase)
        date_diff('day', cpi.last_purchase_date, current_date) as days_since_last_purchase,
        
        -- Category preference rank
        ccr.category_rank,
        
        -- Co-purchase strength (sum of co-purchases with products the customer has bought)
        (
            select coalesce(sum(pc.copurchase_count), 0)
            from product_copurchases pc
            join customer_product_interactions cpi2 on 
                (pc.product_id_1 = cpi2.product_id and pc.product_id_2 = cpi.product_id) or
                (pc.product_id_2 = cpi2.product_id and pc.product_id_1 = cpi.product_id)
            where cpi2.customer_id = cpi.customer_id and cpi2.product_id != cpi.product_id
        ) as copurchase_strength,
        
        -- Customer's average purchase frequency (in days)
        case 
            when cpi.purchase_count > 1
            then date_diff('day', cpi.first_purchase_date, cpi.last_purchase_date) / (cpi.purchase_count - 1)
            else null
        end as avg_purchase_interval_days,
        
        -- Price point preference (average price paid by customer)
        cpi.total_spent / cpi.purchase_count as avg_price_paid
        
    from customer_product_interactions cpi
    left join customer_category_ranks ccr on 
        cpi.customer_id = ccr.customer_id and 
        cpi.product_category_name_english = ccr.product_category_name_english
)

select * from recommendation_features

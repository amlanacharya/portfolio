# Product Performance Mart - Stakeholder Guide

## Business Context

The Product Performance Mart provides a comprehensive view of product performance across multiple dimensions, combining sales data, inventory metrics, customer engagement, and time-based trends. This model serves as the single source of truth for product analytics at VyaparBazaar.

## Purpose

This model enables:
- Product performance analysis and ranking
- Inventory optimization
- Seasonal trend identification
- Customer engagement insights
- Profitability analysis
- Category performance comparison

## Key Metrics and Definitions

### Product Information

| Metric | Definition | Business Use |
|--------|------------|--------------|
| product_id | Unique identifier for the product | Linking across systems |
| product_name | Name of the product | Product identification |
| product_category | Category of the product | Category-level analysis |
| product_subcategory | Subcategory of the product | Detailed categorization |
| date_month | Month of the data | Time-based analysis |

### Sales Metrics

| Metric | Definition | Business Use |
|--------|------------|--------------|
| units_sold | Number of units sold in the given month | Volume analysis |
| revenue | Total revenue generated in the given month | Revenue tracking |
| profit | Total profit generated in the given month | Profitability analysis |
| profit_margin | Profit as a percentage of revenue | Efficiency measurement |
| category_revenue_rank | Revenue rank within the product category | Category performance |
| overall_revenue_rank | Revenue rank across all products | Overall performance |

### Time-Based Trends

| Metric | Definition | Business Use |
|--------|------------|--------------|
| mom_revenue_growth | Month-over-month revenue growth rate | Trend analysis |
| mom_units_growth | Month-over-month units sold growth rate | Volume trend analysis |
| is_festival_season | Flag indicating festival season (Sep-Nov) | Seasonal analysis |
| season | Season of the year | Seasonal patterns |

### Inventory Metrics

| Metric | Definition | Business Use |
|--------|------------|--------------|
| avg_stock_level | Average stock level during the period | Inventory management |
| min_stock_level | Minimum stock level during the period | Stock-out risk |
| avg_days_of_inventory | Average number of days of inventory based on sales rate | Inventory planning |

### Customer Engagement Metrics

| Metric | Definition | Business Use |
|--------|------------|--------------|
| avg_review_score | Average customer review score (1-5) | Customer satisfaction |
| review_count | Number of customer reviews | Engagement level |
| view_to_purchase_ratio | Ratio of purchases to product views | Conversion efficiency |

## Data Freshness and Update Frequency

- **Update Frequency**: Daily at 3:00 AM IST
- **Data Latency**: 24 hours (yesterday's data available today)
- **Historical Range**: Full product history since platform launch
- **Lookback Period**: All metrics available for trailing 12 months

## Known Limitations and Caveats

1. **New Products**: Products with less than 30 days of history may have incomplete metrics, particularly for trend calculations.

2. **Seasonal Variations**: Growth metrics may be affected by seasonal patterns and should be interpreted accordingly.

3. **Review Data**: Review scores are only available for products that have received at least 5 reviews.

4. **Inventory Data**: Inventory metrics are based on end-of-day snapshots and may not reflect intra-day fluctuations.

5. **View Data**: Product view data is collected from online channels only and does not include in-store browsing.

## Example Queries for Common Business Questions

### 1. Identify Top-Performing Products by Category

```sql
select
    product_category,
    product_name,
    revenue,
    units_sold,
    profit_margin,
    category_revenue_rank
from {{ ref('mart_product_performance') }}
where date_month = date_trunc('month', current_date() - interval '1 month')
  and category_revenue_rank <= 5
order by product_category, category_revenue_rank
```

### 2. Find Products with Declining Sales

```sql
select
    product_id,
    product_name,
    product_category,
    revenue,
    mom_revenue_growth,
    units_sold,
    mom_units_growth
from {{ ref('mart_product_performance') }}
where date_month = date_trunc('month', current_date() - interval '1 month')
  and mom_revenue_growth < -0.1
  and revenue > 10000
order by mom_revenue_growth asc
```

### 3. Analyze Seasonal Product Performance

```sql
select
    product_category,
    season,
    sum(revenue) as total_revenue,
    sum(units_sold) as total_units,
    avg(profit_margin) as avg_profit_margin
from {{ ref('mart_product_performance') }}
where date_month >= date_trunc('month', current_date() - interval '1 year')
group by 1, 2
order by 1, 2
```

### 4. Identify Inventory Optimization Opportunities

```sql
select
    product_id,
    product_name,
    product_category,
    avg_stock_level,
    avg_days_of_inventory,
    units_sold,
    revenue
from {{ ref('mart_product_performance') }}
where date_month = date_trunc('month', current_date() - interval '1 month')
  and (avg_days_of_inventory > 90 or avg_days_of_inventory < 15)
  and revenue > 5000
order by avg_days_of_inventory desc
```

## Visualization Recommendations

### 1. Product Performance Dashboard

![Product Performance Dashboard](https://example.com/dashboard_wireframe.png)

**Key Components:**
- Category performance comparison
- Top and bottom performing products
- Month-over-month growth trends
- Seasonal performance patterns
- Profit margin analysis

### 2. Inventory Optimization Dashboard

**Key Components:**
- Stock level vs. sales rate
- Days of inventory distribution
- Stock-out risk indicators
- Excess inventory highlights
- Seasonal inventory planning

### 3. Product Engagement Analysis

**Key Components:**
- Review score trends
- View-to-purchase conversion
- Product popularity metrics
- Customer feedback analysis
- Engagement by product category

## Sample Dashboard Wireframe

```
+-----------------------------------------------+
|                                               |
|  Product Performance Dashboard                |
|                                               |
+---------------+---------------+---------------+
|               |               |               |
| Total         | Total         | Average       |
| Revenue       | Units Sold    | Profit Margin |
| ₹12,345,678   | 45,678        | 24.5%         |
|               |               |               |
+---------------+---------------+---------------+
|                                               |
|  Category Performance                         |
|                                               |
|  [BAR CHART: Revenue by Category]             |
|                                               |
+-------------------+---------------------------+
|                   |                           |
|  Top Products     |  Growth Trends            |
|                   |                           |
|  [TABLE:          |  [LINE CHART:             |
|   Product         |   Month-over-month        |
|   Revenue         |   revenue growth          |
|   Units           |   for top categories]     |
|   Growth          |                           |
|   Margin]         |                           |
|                   |                           |
+-------------------+---------------------------+
|                                               |
|  Seasonal Performance                         |
|                                               |
|  [HEAT MAP: Performance by season/category]   |
|                                               |
+-----------------------------------------------+
|                                               |
|  Inventory Optimization                       |
|                                               |
|  [SCATTER PLOT: Stock level vs. sales rate]   |
|                                               |
+-----------------------------------------------+
```

## Data Dictionary

| Column Name | Data Type | Description | Example Values |
|-------------|-----------|-------------|---------------|
| product_id | string | Unique identifier for the product | 'PROD12345' |
| product_name | string | Name of the product | 'Premium Cotton T-Shirt' |
| product_category | string | Category of the product | 'Apparel', 'Electronics' |
| product_subcategory | string | Subcategory of the product | 'T-Shirts', 'Smartphones' |
| date_month | date | Month of the data | '2023-01-01' |
| units_sold | integer | Number of units sold in the given month | 245 |
| revenue | decimal | Total revenue generated in the given month | 12500.75 |
| profit | decimal | Total profit generated in the given month | 3750.25 |
| profit_margin | decimal | Profit as a percentage of revenue | 30.0 |
| mom_revenue_growth | decimal | Month-over-month revenue growth rate | 0.15 |
| mom_units_growth | decimal | Month-over-month units sold growth rate | 0.12 |
| avg_stock_level | decimal | Average stock level during the period | 500 |
| min_stock_level | integer | Minimum stock level during the period | 50 |
| avg_days_of_inventory | decimal | Average number of days of inventory based on sales rate | 45.5 |
| avg_review_score | decimal | Average customer review score (1-5) | 4.2 |
| review_count | integer | Number of customer reviews | 78 |
| view_to_purchase_ratio | decimal | Ratio of purchases to product views | 0.08 |
| category_revenue_rank | integer | Revenue rank within the product category | 3 |
| overall_revenue_rank | integer | Revenue rank across all products | 127 |
| is_festival_season | boolean | Flag indicating festival season (Sep-Nov) | true, false |
| season | string | Season of the year | 'Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter' |

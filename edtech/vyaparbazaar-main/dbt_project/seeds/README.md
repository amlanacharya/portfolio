# Seeds

This directory contains static data files (seeds) that can be loaded into the database and used in models.

## Available Seeds

### `indian_states.csv`

Contains information about Indian states and union territories, including codes, names, regions, and other metadata.

**Columns:**
- `state_code`: Two-letter code for the state
- `state_name`: Full name of the state
- `region`: Geographic region (North, South, East, West, Northeast, Central)
- `population`: Population count
- `area_sqkm`: Area in square kilometers
- `capital`: Capital city
- `official_language`: Primary official language

### `product_categories.csv`

Contains product category information, including original Portuguese names and English translations.

**Columns:**
- `category_id`: Unique identifier for the category
- `category_name`: Original category name (in Portuguese)
- `category_name_english`: English translation of the category name
- `department`: Department the category belongs to
- `tax_rate`: GST tax rate applicable to the category
- `is_seasonal`: Whether the category has seasonal demand (TRUE/FALSE)
- `season_peak`: Peak season for seasonal categories (Summer, Winter, Spring, Fall)

### `indian_festivals.csv`

Contains information about Indian festivals and their shopping patterns.

**Columns:**
- `festival_id`: Unique identifier for the festival
- `festival_name`: Name of the festival
- `start_date`: Start date of the festival (YYYY-MM-DD)
- `end_date`: End date of the festival (YYYY-MM-DD)
- `is_national`: Whether the festival is celebrated nationally (TRUE/FALSE)
- `region`: Regions where the festival is primarily celebrated
- `shopping_category`: Categories that see increased sales during the festival (pipe-separated)

## Loading Seeds

Seeds are automatically loaded into the database when you run:

```bash
dbt seed
```

This will create tables in the database with the seed data.

## Using Seeds in Models

You can reference seeds in your models using the `ref` function:

```sql
-- Example: Joining with the indian_states seed
SELECT
    c.customer_id,
    c.customer_state,
    s.region,
    s.official_language
FROM {{ ref('stg_customers') }} c
LEFT JOIN {{ ref('indian_states') }} s ON c.customer_state = s.state_code
```

## Updating Seeds

If you update a seed file, you need to reload it:

```bash
dbt seed --select seed_name
```

For example:

```bash
dbt seed --select indian_states
```

## Full Refresh

To force a full refresh of all seeds:

```bash
dbt seed --full-refresh
```

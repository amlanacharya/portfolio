# Module 1: Exercise Solutions

This document provides detailed solutions for the exercises in Module 1 of the VyaparBazaar Analytics Internship Camp.

## Exercise 1.1: Project Exploration

### Step 1: Examine the project structure and identify the different model layers

The VyaparBazaar Analytics project follows a layered approach to data modeling:

1. **Staging Layer** (`models/staging/`):
   - Purpose: Clean, rename, and cast raw data
   - Files: `stg_*.sql`
   - Example: `stg_customers.sql`, `stg_orders.sql`
   - Materialization: Views (for faster development)

2. **Intermediate Layer** (`models/intermediate/`):
   - Purpose: Join and transform staging models
   - Files: `int_*.sql`
   - Example: `int_customer_behavior.sql`
   - Materialization: Tables (for better query performance)

3. **Mart Layer** (`models/marts/`):
   - Purpose: Business-specific models for analysis
   - Files: Organized by business domain
   - Example: `customer_marts/customer_overview.sql`
   - Materialization: Tables (for optimal query performance)

4. **ML Features Layer** (`models/ml_features/`):
   - Purpose: Prepare data for machine learning
   - Files: `*_features.sql`
   - Example: `customer_churn_features.sql`
   - Materialization: Tables (for direct use in ML pipelines)

### Step 2: Run `dbt deps` to install dependencies

```bash
cd dbt_project
dbt deps
```

Expected output:
```
Installing dbt-labs/dbt_utils
  Installed from version 1.1.1
  Up to date!
```

### Step 3: Run `dbt compile` to compile the models

```bash
dbt compile
```

Expected output:
```
Found 25 models, 15 tests, 0 snapshots, 0 analyses, 0 macros, 0 operations, 0 seed files, 0 sources, 0 exposures, 0 metrics, 0 groups

Concurrency: 4 threads (target='dev')

Compiled node "model.vyaparbazaar.stg_customers" (1 of 25)
Compiled node "model.vyaparbazaar.stg_orders" (2 of 25)
...
Compiled node "model.vyaparbazaar.customer_churn_features" (25 of 25)

Finished compiling 25 nodes
```

### Step 4: Explore the compiled SQL in the target directory

Navigate to the `target/compiled/vyaparbazaar/models/` directory to examine the compiled SQL files.

Example of a compiled staging model (`target/compiled/vyaparbazaar/models/staging/stg_customers.sql`):

```sql
with source as (
    select * from vyaparbazaar_customers
),

renamed as (
    select
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state
    from source
)

select * from renamed
```

Example of a compiled intermediate model (`target/compiled/vyaparbazaar/models/intermediate/int_customer_behavior.sql`):

```sql
with customers as (
    select * from vyaparbazaar.staging.stg_customers
),

orders as (
    select * from vyaparbazaar.staging.stg_orders
),

order_items as (
    select * from vyaparbazaar.staging.stg_order_items
),

-- More CTEs...

customer_behavior as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        coalesce(count(distinct o.order_id), 0) as order_count,
        coalesce(sum(oi.price), 0) as total_order_value,
        -- More metrics...
    from customers c
    left join orders o on c.customer_id = o.customer_id
    left join order_items oi on o.order_id = oi.order_id
    -- More joins...
    group by 1, 2, 3, 4
)

select * from customer_behavior
```

## Exercise 1.2: Understanding Model Dependencies

### Step 1: Use `dbt docs serve` to view the documentation

```bash
dbt docs generate
dbt docs serve --port 8081
```

This will start a web server at http://localhost:8081 where you can view the project documentation.

### Step 2: Explore the lineage graph

1. In the dbt documentation interface, click on the "Lineage Graph" tab
2. You'll see a visual representation of all models and their dependencies
3. Models are color-coded by layer:
   - Staging models (blue)
   - Intermediate models (green)
   - Mart models (purple)
   - ML Feature models (orange)
4. Arrows indicate dependencies between models

### Step 3: Identify the dependencies of the `int_customer_behavior` model

The `int_customer_behavior` model depends on:

1. **Direct dependencies**:
   - `stg_customers`
   - `stg_orders`
   - `stg_order_items`
   - `stg_reviews`
   - `stg_clickstream`
   - `stg_app_events`

2. **Indirect dependencies**:
   - Source tables referenced by the staging models

### Step 4: Draw a simple diagram of the data flow

Here's a simplified diagram of the data flow for the `int_customer_behavior` model:

```
Source Tables:
  vyaparbazaar_customers
  vyaparbazaar_orders
  vyaparbazaar_order_items
  vyaparbazaar_reviews
  vyaparbazaar_clickstream
  vyaparbazaar_app_events
        |
        ↓
Staging Models:
  stg_customers
  stg_orders
  stg_order_items
  stg_reviews
  stg_clickstream
  stg_app_events
        |
        ↓
Intermediate Model:
  int_customer_behavior
        |
        ↓
Mart Models:
  customer_overview
  customer_engagement
        |
        ↓
ML Feature Models:
  customer_churn_features
  customer_segmentation_features
```

## Bonus Exercises Solutions

### Bonus 3: Explore macros and tests

The project includes several useful macros in the `macros/` directory:

1. **Date Utils** (`date_utils.sql`):
   - `date_diff_in_days(start_date, end_date)`: Calculate days between dates
   - `is_recent_date(date_column, days=30)`: Check if a date is recent
   - `get_fiscal_year(date_column)`: Get fiscal year for a date
   - `get_fiscal_quarter(date_column)`: Get fiscal quarter for a date
   - `get_season(date_column)`: Get season for a date
   - `is_weekend(date_column)`: Check if a date is a weekend
   - `is_festival_season(date_column)`: Check if a date is during festival season

2. **String Utils** (`string_utils.sql`):
   - `clean_string(column_name)`: Trim and lowercase a string
   - `standardize_state_code(state_column)`: Convert state names to standard codes
   - `extract_domain_from_email(email_column)`: Extract domain from email
   - `categorize_email_domain(email_column)`: Categorize email domains
   - `format_phone_number(phone_column)`: Format phone numbers
   - `get_payment_method_category(payment_method_column)`: Categorize payment methods

The project also includes custom tests in the `tests/` directory:

1. **assert_positive_values**: Tests that a column contains only positive values
2. **assert_date_in_past**: Tests that a date column contains only past dates
3. **assert_valid_percentage**: Tests that a column contains valid percentage values

### Bonus 4: Explore seeds

The project includes several seed files in the `seeds/` directory:

1. **indian_states.csv**: Information about Indian states and territories
2. **product_categories.csv**: Product category information
3. **indian_festivals.csv**: Information about Indian festivals and shopping patterns

After running `dbt seed`, these files are loaded into the database and can be referenced in models using the `ref` function:

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

## Key Takeaways from Module 1 Exercises

1. **Layered Architecture**: The project follows a clear layered architecture that separates concerns and promotes reusability.

2. **Modular SQL**: Each model focuses on a specific transformation, making the code easier to understand and maintain.

3. **Dependencies**: Models build on each other, creating a clear data lineage that can be visualized and understood.

4. **Documentation**: dbt automatically generates documentation that helps understand the project structure and data flow.

5. **Version Control**: All models are SQL files that can be version-controlled, enabling collaboration and change tracking.

6. **Reusable Components**: Macros provide reusable SQL snippets that can be used across models.

7. **Data Quality**: Tests ensure data quality and validate business rules.

8. **Reference Data**: Seeds provide static reference data that can be used in models.

## Next Steps

Now that you understand the project structure and model dependencies, you're ready to move on to Module 2, where you'll learn about data transformation fundamentals and create your own models.

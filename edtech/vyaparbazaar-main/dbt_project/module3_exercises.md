# Module 3: Advanced Data Modeling Techniques - Exercises 🏋️‍♀️

This document contains hands-on exercises for Module 3 of the VyaparBazaar Analytics Internship Camp. These exercises will help you apply the advanced data modeling concepts covered in the module.

## Prerequisites

Before starting these exercises, make sure you have:
1. Completed Module 2 exercises
2. Read through the Module 3 handholding guide
3. Successfully run `dbt deps` to install required packages
4. Verified that dbt can connect to DuckDB with `dbt debug`

## Exercise 3.1: Create a Date Dimension Model

### Objective
Create a comprehensive date dimension model that can be used for time-based analysis across the VyaparBazaar analytics project.

### Instructions

1. Create a new file `dim_date.sql` in the `models/dimensions/` directory (create the directory if it doesn't exist).

2. Use the `dbt_utils.date_spine` macro to generate a date range from January 1, 2016, to December 31, 2023.

3. For each date, include the following attributes:
   - `date_key` (primary key in YYYYMMDD format)
   - `calendar_date` (actual date)
   - `year`, `month`, `day`, `quarter`
   - `day_of_week`, `day_of_year`
   - `is_weekend` (boolean)
   - `is_holiday` (boolean, use a macro to determine Indian holidays)
   - `is_festival_season` (boolean, consider September-November as festival season)
   - `fiscal_year` (April-March)
   - `fiscal_quarter`
   - `season` (Spring, Summer, Monsoon, Autumn, Winter)

4. Configure the model to be materialized as a table.

5. Create a schema.yml file in the dimensions directory with appropriate documentation and tests:
   - Add a unique test for `date_key`
   - Add a not_null test for `date_key` and `calendar_date`
   - Add a test to ensure `day_of_week` is between 0 and 6

### Questions to Consider
1. How can this dimension table be used to analyze seasonal trends in sales?
2. What additional date attributes might be useful for the VyaparBazaar business?
3. How would you handle different time zones if the business operates internationally?

## Exercise 3.2: Build an Order Facts Model

### Objective
Create a fact table for orders that combines data from multiple staging models and implements dimensional modeling concepts.

### Instructions

1. Create a new file `fct_orders.sql` in the `models/facts/` directory (create the directory if it doesn't exist).

2. Join the following staging models:
   - `stg_orders`
   - `stg_order_items`
   - `stg_payments`

3. Include the following metrics and dimensions:
   - `order_id` (primary key)
   - `customer_id` (foreign key to dim_customers)
   - `order_date` (foreign key to dim_date)
   - `order_status`
   - `order_total` (sum of payment values)
   - `item_count` (number of items in the order)
   - `items_price` (sum of item prices)
   - `freight_value` (sum of freight values)
   - `payment_methods` (array of payment types used)
   - `delivery_time_days` (difference between delivery date and purchase date)
   - `is_delayed` (boolean, true if delivered after estimated date)

4. Configure the model to be materialized as a table.

5. Create or update the schema.yml file in the facts directory with appropriate documentation and tests:
   - Add a unique test for `order_id`
   - Add a not_null test for `order_id`, `customer_id`, and `order_date`
   - Add a relationships test for `customer_id` to `dim_customers`
   - Add a relationships test for `order_date` to `dim_date`
   - Add a test to ensure `order_total` equals `items_price` plus `freight_value`

### Questions to Consider
1. What grain (level of detail) is appropriate for this fact table?
2. How would you handle orders with multiple payment methods?
3. What additional metrics might be useful for order analysis?

## Exercise 3.3: Create an Incremental Clickstream Model

### Objective
Create an incremental model for clickstream data that efficiently processes large volumes of event data.

### Instructions

1. Create a new file `int_clickstream_events.sql` in the `models/intermediate/` directory.

2. Configure the model to use incremental materialization with `event_id` as the unique key.

3. Include logic to only process new records since the last run.

4. Transform the clickstream data to include:
   - `event_id` (primary key)
   - `customer_id` (foreign key to dim_customers)
   - `event_date` (foreign key to dim_date)
   - `event_timestamp`
   - `event_type`
   - `page_type`
   - `device_category` (derived from device, e.g., Mobile, Desktop, Tablet)
   - `browser_category` (derived from browser)
   - `session_id`
   - `is_purchase_event` (boolean)
   - `is_cart_event` (boolean)
   - `is_product_view_event` (boolean)

5. Create or update the schema.yml file with appropriate documentation and tests.

### Questions to Consider
1. What are the performance implications of using incremental vs. table materialization for this data?
2. How would you handle schema changes in an incremental model?
3. What strategies could you use to optimize the performance of queries against this large dataset?

## Exercise 3.4: Build a Customer Behavior Mart Model

### Objective
Create a business-focused mart model that leverages the fact and dimension tables to provide insights into customer behavior.

### Instructions

1. Create a new file `customer_behavior.sql` in the `models/marts/customer_marts/` directory (create the directories if they don't exist).

2. Join the following models:
   - `dim_customers`
   - `fct_orders`
   - `int_clickstream_events`

3. Use window functions to calculate:
   - Customer lifetime value
   - Average order value
   - Days between orders
   - Purchase frequency
   - Recency (days since last order)
   - Browsing to purchase conversion rate

4. Create customer segments based on:
   - RFM (Recency, Frequency, Monetary value)
   - Device preference
   - Payment method preference
   - Product category preference

5. Configure the model to be materialized as a table.

6. Create or update the schema.yml file with appropriate documentation and tests.

### Questions to Consider
1. How can this mart model be used by business stakeholders?
2. What visualizations or dashboards could be built from this data?
3. How would you ensure this model remains performant as the data grows?

## Exercise 3.5: Implement Advanced Testing

### Objective
Implement advanced testing strategies to ensure data quality across your models.

### Instructions

1. Create a custom generic test in the `tests/generic/` directory (create the directory if it doesn't exist):
   - `test_values_in_range.sql` - Test that values in a column fall within a specified range
   - `test_values_increasing.sql` - Test that values are increasing over time for a given entity

2. Apply these tests to your models in the appropriate schema.yml files.

3. Install the dbt-expectations package and add at least three expectations tests to your models.

4. Create a singular test in the `tests/singular/` directory that validates a specific business rule:
   - For example, test that the total sales in `fct_orders` matches the total sales in the source data

5. Run `dbt test` to verify all tests pass.

### Questions to Consider
1. What are the most critical data quality issues to test for in an e-commerce dataset?
2. How would you handle test failures in a production environment?
3. How can you balance comprehensive testing with build performance?

## Bonus Challenge: Create a Product Performance Analysis Model

### Objective
Create an advanced analysis model that provides insights into product performance across different dimensions.

### Instructions

1. Create a new file `product_performance.sql` in the `models/marts/product_marts/` directory.

2. Join product data with orders, customers, and time dimensions.

3. Use advanced SQL techniques to analyze:
   - Product sales trends over time
   - Product affinity (which products are often purchased together)
   - Product returns and customer satisfaction
   - Regional variations in product popularity
   - Seasonal trends in product categories

4. Use Jinja templating to make the analysis configurable (e.g., time period, product categories).

5. Document your model thoroughly and add appropriate tests.

## Submission

After completing the exercises, prepare a brief summary of your work:

1. Key learnings from implementing dimensional modeling
2. Challenges encountered and how you resolved them
3. Insights gained from the customer behavior and product performance models
4. Suggestions for further improvements to the data models

## Next Steps

After completing these exercises, you'll be ready to move on to Module 4, where you'll learn about advanced analytics techniques, metrics, and dashboard integration.

Happy modeling! 🚀

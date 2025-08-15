# Module 2: Data Transformation Fundamentals - Exercises

This document contains hands-on exercises for Module 2 of the VyaparBazaar Analytics Internship Camp. These exercises will help you apply the concepts of SQL basics in dbt, Jinja templating, macros, sources and references, and testing.

## Exercise 2.1: Create a New Staging Model

### Objective
Create a new staging model for the support tickets data source.

### Instructions

1. Examine the `sources.yml` file to understand the structure of the `vyaparbazaar_support_tickets` source.

2. Create a new file `stg_support_tickets.sql` in the `models/staging/` directory with the following structure:
   ```sql
   with source as (
       select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_support_tickets') }}
   ),

   renamed as (
       -- Your code here: select and rename/cast columns
   )

   select * from renamed
   ```

3. In the `renamed` CTE, select all columns from the source, renaming them if necessary and casting date/timestamp columns to the appropriate types.

4. Run your model with:
   ```bash
   dbt run -m stg_support_tickets
   ```

5. Add your model to the `models/staging/schema.yml` file with appropriate descriptions and tests:
   - Add a unique test for `ticket_id`
   - Add a not_null test for `ticket_id` and `customer_id`
   - Add a relationships test for `customer_id` to `stg_customers`
   - Add an accepted_values test for `status` with appropriate values

### Questions to Consider
1. What columns should be cast to specific data types?
2. What naming conventions should you follow?
3. What tests are appropriate for this model?

## Exercise 2.2: Use Jinja Templating for Dynamic SQL

### Objective
Create a model that uses Jinja templating to generate dynamic SQL.

### Instructions

1. Create a new file `int_support_ticket_summary.sql` in the `models/intermediate/` directory.

2. Use Jinja to create a model that summarizes support tickets by category and status:
   ```sql
   {% set status_values = ['open', 'in_progress', 'resolved', 'closed', 'cancelled'] %}

   with support_tickets as (
       select * from {{ ref('stg_support_tickets') }}
   ),

   ticket_summary as (
       select
           category,
           count(*) as total_tickets,
           {% for status in status_values %}
           sum(case when status = '{{ status }}' then 1 else 0 end) as {{ status }}_tickets,
           {% endfor %}
           avg(datediff('hour', created_at, resolved_at)) as avg_resolution_time_hours
       from support_tickets
       group by 1
   )

   select * from ticket_summary
   ```

3. Modify the code to handle any missing status values in your data.

4. Run your model with:
   ```bash
   dbt run -m int_support_ticket_summary
   ```

5. Add your model to the `models/intermediate/schema.yml` file with appropriate descriptions.

### Questions to Consider
1. How does Jinja make this SQL more maintainable?
2. What would happen if a new status value was added?
3. How could you make this model more dynamic?

## Exercise 2.3: Create and Use a Custom Macro

### Objective
Create a custom macro and use it in a model.

### Instructions

1. Create a new file `support_utils.sql` in the `macros/` directory with the following content:
   ```sql
   {% macro calculate_resolution_time(created_at, resolved_at, unit='hour') %}
       case
           when {{ resolved_at }} is null then null
           when {{ unit }} = 'minute' then datediff('minute', {{ created_at }}, {{ resolved_at }})
           when {{ unit }} = 'hour' then datediff('hour', {{ created_at }}, {{ resolved_at }})
           when {{ unit }} = 'day' then datediff('day', {{ created_at }}, {{ resolved_at }})
           else datediff('hour', {{ created_at }}, {{ resolved_at }})
       end
   {% endmacro %}

   {% macro categorize_resolution_time(resolution_time_hours) %}
       case
           when {{ resolution_time_hours }} is null then 'Unresolved'
           when {{ resolution_time_hours }} <= 1 then 'Under 1 hour'
           when {{ resolution_time_hours }} <= 4 then '1-4 hours'
           when {{ resolution_time_hours }} <= 24 then '4-24 hours'
           when {{ resolution_time_hours }} <= 72 then '1-3 days'
           else 'Over 3 days'
       end
   {% endmacro %}
   ```

2. Create a new file `int_customer_support_performance.sql` in the `models/intermediate/` directory that uses your macros:
   ```sql
   with support_tickets as (
       select * from {{ ref('stg_support_tickets') }}
   ),

   ticket_metrics as (
       select
           ticket_id,
           customer_id,
           category,
           created_at,
           resolved_at,
           {{ calculate_resolution_time('created_at', 'resolved_at', 'hour') }} as resolution_time_hours,
           satisfaction_rating
       from support_tickets
   ),

   ticket_categories as (
       select
           ticket_id,
           customer_id,
           category,
           resolution_time_hours,
           {{ categorize_resolution_time('resolution_time_hours') }} as resolution_time_category,
           satisfaction_rating
       from ticket_metrics
   )

   select * from ticket_categories
   ```

3. Run your model with:
   ```bash
   dbt run -m int_customer_support_performance
   ```

4. Add your model to the `models/intermediate/schema.yml` file with appropriate descriptions.

### Questions to Consider
1. How do macros improve code reusability?
2. What other macros could be useful for support ticket analysis?
3. How could you extend these macros for more functionality?

## Exercise 2.4: Add Tests to Your Models

### Objective
Add comprehensive tests to your new models.

### Instructions

1. Update the `models/intermediate/schema.yml` file to add tests to your new intermediate models:
   ```yaml
   models:
     - name: int_support_ticket_summary
       description: "Summary of support tickets by category and status"
       columns:
         - name: category
           description: "Support ticket category"
           tests:
             - not_null
             - unique
         - name: total_tickets
           description: "Total number of tickets in this category"
           tests:
             - not_null
             - assert_positive_values
         # Add tests for other columns

     - name: int_customer_support_performance
       description: "Support ticket performance metrics"
       columns:
         - name: ticket_id
           description: "Unique identifier for the support ticket"
           tests:
             - unique
             - not_null
         # Add tests for other columns
   ```

2. Create a new custom test `assert_valid_satisfaction_rating.sql` in the `tests/` directory:
   ```sql
   {% test assert_valid_satisfaction_rating(model, column_name) %}

   with validation as (
       select
           {{ column_name }} as rating
       from {{ model }}
   ),

   validation_errors as (
       select
           rating
       from validation
       where rating is not null and (rating < 1 or rating > 5)
   )

   select *
   from validation_errors

   {% endtest %}
   ```

3. Apply this test to the `satisfaction_rating` column in your `int_customer_support_performance` model.

4. Run all tests with:
   ```bash
   dbt test
   ```

5. Fix any failing tests by updating your models.

### Questions to Consider
1. What other tests would be valuable for these models?
2. How do tests help ensure data quality?
3. What happens when a test fails?

## Exercise 2.5: Create a Mart Model Using Sources and References

### Objective
Create a business-focused mart model that combines data from multiple sources and references.

### Instructions

1. Create a new file `customer_support_mart.sql` in the `models/marts/` directory:
   ```sql
   with customers as (
       select * from {{ ref('stg_customers') }}
   ),

   orders as (
       select * from {{ ref('int_orders_with_items') }}
   ),

   support_performance as (
       select * from {{ ref('int_customer_support_performance') }}
   ),

   customer_orders as (
       select
           customer_id,
           count(distinct order_id) as order_count,
           sum(payment_value) as total_spend
       from orders
       group by 1
   ),

   customer_support as (
       select
           customer_id,
           count(*) as ticket_count,
           avg(resolution_time_hours) as avg_resolution_time,
           avg(satisfaction_rating) as avg_satisfaction
       from support_performance
       group by 1
   ),

   final as (
       select
           c.customer_id,
           c.customer_unique_id,
           c.customer_city,
           c.customer_state,
           coalesce(co.order_count, 0) as order_count,
           coalesce(co.total_spend, 0) as total_spend,
           coalesce(cs.ticket_count, 0) as ticket_count,
           cs.avg_resolution_time,
           cs.avg_satisfaction,
           case
               when cs.ticket_count = 0 then 'No Support Interaction'
               when cs.avg_satisfaction >= 4 then 'Highly Satisfied'
               when cs.avg_satisfaction >= 3 then 'Satisfied'
               when cs.avg_satisfaction < 3 then 'Dissatisfied'
               else 'Unknown'
           end as satisfaction_segment
       from customers c
       left join customer_orders co on c.customer_id = co.customer_id
       left join customer_support cs on c.customer_id = cs.customer_id
   )

   select * from final
   ```

2. Run your model with:
   ```bash
   dbt run -m customer_support_mart
   ```

3. Add your model to the `models/marts/schema.yml` file with appropriate descriptions and tests.

### Questions to Consider
1. How does this mart model provide business value?
2. What other data could be incorporated?
3. How would you document this model for business users?

## Bonus Challenge: Create an Incremental Model

### Objective
Convert an existing model to use incremental materialization.

### Instructions

1. Modify your `stg_support_tickets.sql` model to use incremental materialization:
   ```sql
   {{
       config(
           materialized='incremental',
           unique_key='ticket_id'
       )
   }}

   with source as (
       select * from {{ source('vyaparbazaar_raw', 'vyaparbazaar_support_tickets') }}
       {% if is_incremental() %}
       where created_at > (select max(created_at) from {{ this }})
       {% endif %}
   ),

   renamed as (
       -- Your existing transformation logic
   )

   select * from renamed
   ```

2. Run your incremental model:
   ```bash
   dbt run -m stg_support_tickets
   ```

3. Explain the benefits and trade-offs of using incremental materialization.

## Submission

After completing these exercises, make sure to:
1. Run `dbt test` to ensure all tests pass
2. Run `dbt docs generate` to update documentation
3. Review your work and prepare to discuss your solutions

Good luck!

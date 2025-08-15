# Module 5: Analytics Engineering Best Practices - Exercises 🏋️‍♀️

This document contains hands-on exercises for Module 5 of the VyaparBazaar Analytics Internship Camp. These exercises will help you apply the advanced analytics engineering best practices covered in the module.

## Prerequisites

Before starting these exercises, make sure you have:
1. Completed Module 4 exercises
2. Read through the Module 5 handholding guide
3. Successfully run `dbt deps` to install required packages
4. Verified that dbt can connect to DuckDB with `dbt debug`

## Exercise 5.1: Optimize a Complex Model

### Objective
Optimize an existing complex model to improve its performance while maintaining the same business logic.

### Instructions

1. Examine the `int_customer_behavior` model in the `models/intermediate/` directory.

2. Create a new optimized version called `int_customer_behavior_optimized.sql` with the following improvements:
   - Apply early filtering to reduce data volume
   - Use appropriate join strategies
   - Implement efficient aggregations
   - Add appropriate comments explaining your optimization choices

3. Configure the model with the appropriate materialization strategy based on its usage patterns.

4. Add tests to ensure the optimized model produces the same results as the original.

### Questions to Consider
1. What performance bottlenecks did you identify in the original model?
2. How did your optimizations address these bottlenecks?
3. What materialization strategy did you choose and why?
4. How would you measure the performance improvement?

## Exercise 5.2: Implement Incremental Loading

### Objective
Convert a full-refresh model to an incremental model to improve processing efficiency for large datasets.

### Instructions

1. Examine the `stg_clickstream.sql` model in the `models/staging/` directory.

2. Create a new version called `stg_clickstream_incremental.sql` that:
   - Uses incremental materialization
   - Processes only new data since the last run
   - Handles potential duplicates appropriately
   - Includes appropriate documentation

3. Configure the model with the following parameters:
   - `unique_key`: 'event_id'
   - `incremental_strategy`: 'delete+insert'

4. Add tests to ensure data integrity, especially around the incremental logic.

### Questions to Consider
1. What are the trade-offs of using incremental vs. full-refresh for this model?
2. How would you handle schema changes in an incremental model?
3. What monitoring would you put in place to ensure the incremental model stays healthy?
4. In what scenarios might the incremental approach fail?

## Exercise 5.3: Create a Mart Model with Advanced Materializations

### Objective
Create a business-focused mart model that uses advanced materialization techniques for optimal performance.

### Instructions

1. Create a new mart model called `mart_product_performance.sql` in the `models/marts/` directory that:
   - Combines data from various sources to provide a comprehensive view of product performance
   - Uses appropriate materialization strategies
   - Implements partitioning and/or clustering if applicable

2. The model should include the following metrics:
   - Product details (name, category, etc.)
   - Sales metrics (units sold, revenue, profit margin)
   - Time-based trends (week-over-week, month-over-month growth)
   - Inventory metrics (stock levels, days of inventory)
   - Customer engagement metrics (view-to-purchase ratio, review score)

3. Configure the model with appropriate materialization settings based on the data volume and query patterns.

4. Add comprehensive documentation and tests.

### Questions to Consider
1. Why did you choose the specific materialization strategy?
2. How would your approach change if this data needed to be near real-time?
3. What are the performance implications of the joins and aggregations in your model?
4. How would you optimize this model for different types of queries?

## Exercise 5.4: Develop a Deployment Strategy

### Objective
Design a deployment and scheduling strategy for the VyaparBazaar analytics pipeline.

### Instructions

1. Create a markdown document called `deployment_strategy.md` that outlines:
   - Environment setup (dev, staging, prod)
   - CI/CD pipeline configuration
   - Scheduling recommendations
   - Monitoring and alerting approach

2. Include a diagram showing the flow of data through the environments.

3. Create a sample schedule for model runs based on:
   - Data dependencies
   - Business requirements
   - Resource constraints

4. Document your approach to handling failures and data quality issues.

### Questions to Consider
1. How would you handle emergency fixes that need to be deployed quickly?
2. What metrics would you track to ensure the health of your deployment?
3. How would you balance the need for fresh data with system performance?
4. What stakeholders would need to be involved in the deployment process?

## Exercise 5.5: Stakeholder Documentation

### Objective
Create comprehensive documentation for business stakeholders to understand and use the analytics models effectively.

### Instructions

1. Choose one of the mart models you've worked with during the camp.

2. Create a markdown document called `stakeholder_guide.md` that includes:
   - Business context and purpose of the model
   - Key metrics and their definitions
   - Data freshness and update frequency
   - Known limitations or caveats
   - Example queries for common business questions
   - Visualization recommendations

3. Create a sample dashboard wireframe that would effectively present the data from this model.

4. Include a data dictionary that explains each column in business terms.

### Questions to Consider
1. How would you tailor this documentation for different types of stakeholders?
2. What technical details should be included or excluded for business users?
3. How would you gather feedback on the usefulness of the documentation?
4. How would you keep the documentation up-to-date as the models evolve?

## Bonus Exercise: End-to-End Project Optimization

### Objective
Perform a comprehensive review of the entire VyaparBazaar analytics project and propose optimizations across all layers.

### Instructions

1. Create a document called `project_optimization.md` that includes:
   - Performance analysis of current models
   - Recommendations for materialization strategies
   - Suggestions for structural improvements
   - Testing and documentation enhancements

2. Implement at least three of your recommended optimizations.

3. Measure and document the impact of your changes.

4. Present your findings and recommendations as if you were reporting to the analytics team lead.

### Questions to Consider
1. What were the biggest opportunities for improvement in the project?
2. How did you prioritize which optimizations to implement?
3. What was the overall impact of your changes?
4. What further improvements would you recommend for the future?

## Submission Guidelines

For each exercise:
1. Create the required files in your dbt project
2. Add appropriate documentation and tests
3. Run `dbt build` to ensure everything works correctly
4. Document your approach and findings

Good luck! 🚀

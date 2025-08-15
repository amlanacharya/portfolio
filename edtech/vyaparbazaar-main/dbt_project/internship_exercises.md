# VyaparBazaar Analytics Internship Camp Exercises

This document contains hands-on exercises for the VyaparBazaar Analytics Internship Camp. Each exercise is designed to build on the concepts covered in the learning modules.

## Module 1: Introduction to dbt and Data Modeling

### Exercise 1.1: Project Exploration
1. Examine the project structure and identify the different model layers
2. Run `dbt deps` to install dependencies
3. Run `dbt compile` to compile the models
4. Explore the compiled SQL in the target directory

### Exercise 1.2: Understanding Model Dependencies
1. Use `dbt docs serve` to view the documentation
2. Explore the lineage graph
3. Identify the dependencies of the `int_customer_behavior` model
4. Draw a simple diagram of the data flow

## Module 2: Data Transformation Fundamentals

### Exercise 2.1: Create a New Staging Model
1. Create a new staging model for marketing campaigns
2. Include appropriate column renaming and type casting
3. Run `dbt run -m <your_model_name>` to test your model
4. Add your model to the appropriate YAML file

### Exercise 2.2: Source Configuration
1. Add a new source to the `sources.yml` file
2. Create a staging model that references this source
3. Add tests to validate the source data
4. Document the source and its columns

## Module 3: Advanced Data Modeling

### Exercise 3.1: Enhance Customer Behavior Model
1. Add a new metric to the `int_customer_behavior.sql` model:
   - Calculate the ratio of mobile to desktop usage
   - Add a customer engagement score based on activity
2. Run the model and verify your changes
3. Update documentation to reflect your changes

### Exercise 3.2: Create a New Intermediate Model
1. Create a new model called `int_product_performance.sql`
2. Include metrics like:
   - Product view-to-purchase ratio
   - Average review score by product
   - Return rate by product
3. Join with existing models as needed
4. Add appropriate tests

## Module 4: Testing and Documentation

### Exercise 4.1: Add Tests to Models
1. Add the following tests to existing models:
   - Not null tests for primary keys
   - Unique tests for IDs
   - Accepted value tests for status fields
   - Relationship tests between models
2. Run `dbt test` to validate your tests

### Exercise 4.2: Enhance Documentation
1. Add descriptions to all columns in the `int_customer_behavior` model
2. Create a markdown file explaining the business logic
3. Regenerate documentation and explore the changes

## Module 5: Analytics Engineering Best Practices

### Exercise 5.1: Optimize a Complex Model
1. Analyze the performance of the `int_customer_behavior` model
2. Identify opportunities for optimization:
   - Simplify complex joins
   - Improve CTE structure
   - Add materialization strategies
3. Implement your optimizations
4. Measure the performance improvement

### Exercise 5.2: Create a Mart Model
1. Create a new mart model that combines customer behavior with product performance
2. Design the model for business users
3. Include clear naming and documentation
4. Present your model to the group

## Final Project

### Customer Segmentation Model
1. Create a new model in the ml_features folder called `customer_segmentation_features.sql`
2. Use the `int_customer_behavior` model as a base
3. Add features that would be useful for segmentation:
   - Recency (days since last order)
   - Frequency (number of orders)
   - Monetary value (total spend)
   - Product category preferences
   - Channel preferences
4. Document your approach and reasoning
5. Present your model and explain how it could be used for segmentation

## Bonus Challenges

### Incremental Models
1. Convert an existing model to use incremental materialization
2. Explain the benefits and trade-offs

### Custom Macros
1. Create a custom macro to standardize date calculations
2. Apply your macro to existing models

### Advanced Testing
1. Create a custom data quality test
2. Apply it to relevant models

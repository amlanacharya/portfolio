# Module 4: ML Feature Engineering and Explainable Analytics - Exercises 🏋️‍♀️

This document contains hands-on exercises for Module 4 of the VyaparBazaar Analytics Internship Camp. These exercises will help you apply the ML feature engineering and explainable analytics concepts covered in the module.

## Prerequisites

Before starting these exercises, make sure you have:
1. Completed Module 3 exercises
2. Read through the Module 4 handholding guide
3. Successfully run `dbt deps` to install required packages
4. Verified that dbt can connect to DuckDB with `dbt debug`

## Exercise 4.1: Enhance Customer Churn Features

### Objective
Enhance the existing customer churn features model with additional features that could improve churn prediction accuracy.

### Instructions

1. Examine the existing `customer_churn_features.sql` model in the `models/ml_features/` directory to understand the current implementation.

2. Create a new file `customer_churn_features_v2.sql` in the `models/ml_features/` directory.

3. Start with the existing features and add the following new features:
   - `order_frequency_last_90_days`: Number of orders in the last 90 days
   - `order_frequency_last_30_days`: Number of orders in the last 30 days
   - `order_value_trend`: Ratio of average order value in last 3 orders compared to all-time average
   - `days_between_first_second_order`: Days between first and second order (null if fewer than 2 orders)
   - `product_category_diversity`: Number of unique product categories purchased
   - `has_returned_item`: Boolean indicating if the customer has ever returned an item
   - `refund_rate`: Percentage of orders that resulted in refunds
   - `weekend_shopper_ratio`: Percentage of orders placed on weekends
   - `evening_shopper_ratio`: Percentage of orders placed in evening hours (6 PM - midnight)

4. Use appropriate CTEs to organize your SQL code and make it readable.

5. Update the schema.yml file to include documentation for all new features.

6. Add appropriate tests for the new features, including:
   - Not null tests for key features
   - Range tests for ratio features (should be between 0 and 1)
   - Custom tests for any complex business logic

### Questions to Consider
1. Which of these new features do you think would be most predictive of churn? Why?
2. How would you handle missing values for features like `days_between_first_second_order` for customers with only one order?
3. What additional data sources might improve churn prediction that aren't currently being used?

## Exercise 4.2: Create Product Recommendation Features

### Objective
Create a feature model that can be used for product recommendation systems.

### Instructions

1. Create a new file `product_recommendation_features.sql` in the `models/ml_features/` directory.

2. The model should generate features at the customer-product level (i.e., each row represents a customer's relationship with a specific product).

3. Include the following features:
   - `customer_id`: Customer identifier
   - `product_id`: Product identifier
   - `product_category_name_english`: Product category name in English
   - `purchase_count`: Number of times the customer purchased this product
   - `total_spent`: Total amount spent by the customer on this product
   - `days_since_last_purchase`: Number of days since the customer last purchased this product
   - `category_rank`: Rank of this category in the customer's preferences (based on purchase count)
   - `copurchase_count`: Number of times this product was purchased with other products
   - `view_count`: Number of times the customer viewed this product (from clickstream data)
   - `cart_count`: Number of times the customer added this product to cart
   - `purchase_to_view_ratio`: Ratio of purchases to views for this product

4. Create a schema.yml file with documentation for all features.

5. Add appropriate tests for the features.

### Questions to Consider
1. How would you use these features to generate product recommendations?
2. What challenges might arise when implementing this in production?
3. How could you incorporate time-based decay to give more weight to recent interactions?

## Exercise 4.3: Build Customer Segmentation Features

### Objective
Create a feature model for customer segmentation that combines RFM analysis with behavioral and demographic features.

### Instructions

1. Create a new file `customer_segmentation_features.sql` in the `models/ml_features/` directory.

2. Include the following feature categories:

   **RFM Features:**
   - `recency_days`: Days since last order
   - `frequency`: Number of orders
   - `monetary_value`: Average order value

   **Behavioral Features:**
   - `preferred_product_category`: Most frequently purchased product category
   - `preferred_payment_method`: Most frequently used payment method
   - `average_review_score`: Average review score given by the customer
   - `browser_preference`: Most commonly used browser
   - `device_preference`: Most commonly used device
   - `session_duration_avg`: Average session duration in minutes

   **Purchase Pattern Features:**
   - `weekend_shopper`: Boolean, true if >50% of orders are on weekends
   - `evening_shopper`: Boolean, true if >50% of orders are in evening hours
   - `discount_hunter`: Boolean, true if >50% of purchases used promotions
   - `installment_payer`: Boolean, true if >50% of purchases used installments
   - `category_loyalty`: Percentage of purchases in top category

   **Demographic Features:**
   - `customer_state`: Customer's state
   - `customer_city`: Customer's city

3. Create a schema.yml file with documentation for all features.

4. Add appropriate tests for the features.

### Questions to Consider
1. How would you use these features to create meaningful customer segments?
2. What clustering algorithms might be appropriate for this data?
3. How would you validate that your segments are meaningful from a business perspective?

## Exercise 4.4: Implement Feature Documentation and Testing

### Objective
Enhance the documentation and testing for all ML feature models to ensure they are well-documented and reliable.

### Instructions

1. Review all existing ML feature models in the `models/ml_features/` directory.

2. Update the schema.yml file to ensure all features have:
   - Clear descriptions explaining what the feature represents
   - Business context for why the feature is important
   - Information about the expected range or distribution
   - Any caveats or limitations

3. Implement the following tests for all feature models:
   - Not null tests for key features
   - Uniqueness tests for identifier columns
   - Range tests for ratio and percentage features
   - Accepted values tests for categorical features

4. Create at least two custom generic tests that are relevant for ML features:
   - `test_correlation_with_target.sql`: Tests if a feature has a minimum correlation with a target variable
   - `test_feature_variance.sql`: Tests if a feature has sufficient variance to be useful

5. Apply these custom tests to appropriate features in your models.

### Questions to Consider
1. How does comprehensive documentation improve the usability of ML features?
2. What are the risks of using features that haven't been properly tested?
3. How would you handle features that fail tests in a production environment?

## Exercise 4.5: Create an Explainable AI Demo

### Objective
Create a simple Python script that demonstrates how to use the ML features you've created with an explainable AI approach.

### Instructions

1. Create a new file `explainable_ai_demo.py` in the `scripts/` directory.

2. The script should:
   - Connect to the DuckDB database
   - Load data from one of your feature models (e.g., `customer_churn_features`)
   - Train a simple model (e.g., RandomForest) on the data
   - Generate SHAP values to explain the model's predictions
   - Visualize feature importance
   - Provide example explanations for individual predictions

3. Include comments explaining each step of the process.

4. Make sure the script handles missing values and data types appropriately.

### Questions to Consider
1. How do explainability techniques like SHAP help build trust in ML models?
2. What are the limitations of these explainability approaches?
3. How would you communicate model explanations to business stakeholders?

## Bonus Exercise: Feature Store Concept

### Objective
Design a simple feature store concept for VyaparBazaar that would allow features to be reused across multiple ML models.

### Instructions

1. Create a markdown file `feature_store_design.md` that outlines:
   - The structure of your feature store
   - How features would be organized and categorized
   - The metadata that would be stored for each feature
   - How point-in-time correctness would be handled
   - How features would be accessed by ML models
   - How feature versioning would work

2. Create a sample implementation of one component of your feature store design.

### Questions to Consider
1. What are the benefits of a feature store compared to ad-hoc feature engineering?
2. How would a feature store integrate with the existing dbt workflow?
3. What challenges might arise when implementing a feature store?

## Submission Guidelines

For each exercise:
1. Create the required SQL files in the appropriate directories
2. Update schema.yml files with documentation and tests
3. Run `dbt compile` to check for syntax errors
4. Run `dbt test` to verify your tests pass
5. Be prepared to explain your approach and answer questions about your implementation

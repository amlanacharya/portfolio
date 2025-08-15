# VyaparBazaar Analytics Platform

A comprehensive analytics platform for VyaparBazaar, a leading Indian e-commerce marketplace. This project demonstrates the power of combining DuckDB and dbt for building production-grade analytics solutions with explainable AI capabilities.

## Project Overview

VyaparBazaar Analytics Platform provides a complete data pipeline that:

1. Processes customer data from multiple sources
2. Transforms raw data into analytics-ready models
3. Creates ML-ready features for customer insights
4. Enables explainable predictions and segmentation

## Key Features

- **End-to-end Data Pipeline**: From raw data to ML-ready features
- **Customer 360° View**: Comprehensive customer profiles combining transactional, behavioral, and engagement data
- **Explainable ML Features**: Ready-to-use features for churn prediction, LTV forecasting, and segmentation
- **Modular dbt Models**: Well-structured transformation logic with clear lineage
- **DuckDB Integration**: Leveraging DuckDB's analytical query performance

## Project Structure

```
vyaparbazaar_analytics/
├── data/
│   ├── raw/                  # Raw data files
│   ├── transformed/          # Transformed data files
│   └── vyaparbazaar.duckdb   # DuckDB database
├── dbt_project/
│   ├── models/
│   │   ├── staging/          # Raw data models
│   │   ├── intermediate/     # Transformed/joined models
│   │   ├── marts/            # Business-specific models
│   │   └── ml_features/      # ML-ready feature models
│   ├── macros/               # dbt macros
│   ├── tests/                # dbt tests
│   ├── seeds/                # dbt seeds
│   ├── dbt_project.yml       # dbt project configuration
│   └── profiles.yml          # dbt connection profiles
├── scripts/
│   ├── download_data.py      # Script to download OLIST dataset
│   ├── transform_to_vyaparbazaar.py  # Transform data to VyaparBazaar format
│   ├── generate_synthetic_data.py    # Generate additional synthetic data
│   └── load_data_to_duckdb.py        # Load data into DuckDB
├── run_pipeline.py           # Script to run the entire pipeline
└── requirements.txt          # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.8+
- Kaggle API credentials (for downloading the dataset)
- dbt 1.5+
- DuckDB 0.8+

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up Kaggle API credentials:
   - Go to https://www.kaggle.com/account
   - Create a new API token
   - Save the kaggle.json file to ~/.kaggle/kaggle.json
   - Ensure the file has permissions 600 (chmod 600 ~/.kaggle/kaggle.json)

### Running the Pipeline

To run the entire pipeline:

```
python run_pipeline.py
```

This will:
1. Download the OLIST dataset
2. Transform it into VyaparBazaar data
3. Generate additional synthetic data
4. Load data into DuckDB
5. Run dbt models

### Exploring the Data

After running the pipeline, you can:

1. Connect to the DuckDB database:
   ```python
   import duckdb
   con = duckdb.connect('data/vyaparbazaar.duckdb')
   ```

2. Query the transformed models:
   ```sql
   SELECT * FROM customer_segmentation_features LIMIT 10;
   ```

3. View dbt documentation:
   ```
   cd dbt_project
   dbt docs serve
   ```

## Data Models

### Staging Models
Basic cleaned versions of the raw data tables:
- `stg_customers`
- `stg_orders`
- `stg_order_items`
- `stg_products`
- `stg_sellers`
- `stg_payments`
- `stg_reviews`
- `stg_clickstream`
- `stg_support_tickets`
- `stg_marketing_campaigns`
- `stg_app_usage`

### Intermediate Models
Joined and enriched data models:
- `int_orders_with_items`: Orders with item details and metrics
- `int_customer_orders`: Customer order history and metrics
- `int_product_orders`: Product order history and metrics
- `int_customer_behavior`: Comprehensive customer behavior profiles

### ML Feature Models
Ready-to-use features for machine learning:
- `customer_churn_features`: Features for predicting customer churn
- `customer_ltv_features`: Features for predicting customer lifetime value
- `customer_segmentation_features`: Features for customer segmentation
- `product_recommendation_features`: Features for product recommendations

## Explainable AI Use Cases

This project supports several explainable AI use cases:

1. **Customer Churn Prediction**: Identify customers at risk of churning with clear explanations of risk factors
2. **Customer Lifetime Value Forecasting**: Predict future customer value with transparent reasoning
3. **Customer Segmentation**: Create meaningful customer segments with clear defining characteristics
4. **Product Recommendations**: Generate explainable product recommendations based on purchase patterns

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses a transformed version of the [Brazilian E-commerce Public Dataset by OLIST](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- Special thanks to the dbt and DuckDB communities for their excellent tools

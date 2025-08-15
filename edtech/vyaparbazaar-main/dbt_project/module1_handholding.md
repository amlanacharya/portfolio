# Module 1: Introduction to dbt and DuckDB

Welcome to the first module of the VyaparBazaar Analytics Internship Camp! This module introduces you to the powerful combination of **DuckDB** and **dbt (data build tool)** that forms the foundation of modern analytics engineering.

## 🚀 Learning Objectives

By the end of this module, you will:
- Understand why DuckDB and dbt are game-changers for analytics
- Set up your development environment
- Explore the project structure
- Understand the core concepts of data modeling with dbt
- Run your first dbt commands

## 📊 Why DuckDB and dbt?

### The Traditional Data Analytics Challenges

Traditional data analytics workflows often face several challenges:

1. **Data Processing Bottlenecks**: Tools like pandas struggle with large datasets that don't fit in memory
2. **Lack of Version Control**: SQL queries in notebooks or scripts are hard to version control
3. **Poor Documentation**: SQL transformations often lack proper documentation
4. **Testing Gaps**: Data quality testing is often an afterthought
5. **Reproducibility Issues**: Complex data pipelines are difficult to reproduce

### Enter DuckDB: The Analytics Swiss Army Knife

![DuckDB Logo](https://duckdb.org/images/logo-dl/DuckDB_Logo.png)

**DuckDB** is an in-process analytical database designed to overcome these challenges:

#### 🔥 Why DuckDB Instead of Pandas?

| Feature | DuckDB | Pandas |
|---------|--------|--------|
| **Performance** | Optimized for analytical queries with vectorized execution | Limited by Python's performance and single-threaded operations |
| **Memory Usage** | Efficient columnar storage with out-of-core processing | Requires entire dataset to fit in memory |
| **SQL Support** | Full SQL support with advanced analytical functions | Limited SQL-like operations through APIs |
| **Scalability** | Can handle multi-GB datasets on a laptop | Performance degrades with large datasets |
| **Integration** | Seamless integration with Python, R, and other tools | Limited to Python ecosystem |

#### Key DuckDB Advantages:

1. **Speed**: DuckDB is often 10-100x faster than pandas for analytical queries
2. **SQL-First**: Use familiar SQL syntax for complex transformations
3. **Memory Efficiency**: Process datasets larger than RAM
4. **Portability**: Single file database with no server setup
5. **Ecosystem Integration**: Works with Python, R, and other data tools

### dbt: Transforming How We Transform Data

![dbt Logo](https://www.getdbt.com/ui/img/logos/dbt-logo.svg)

**dbt (data build tool)** brings software engineering best practices to data transformations:

#### Key dbt Advantages:

1. **Modularity**: Break complex transformations into manageable, reusable pieces
2. **Version Control**: Track changes to your data models over time
3. **Testing**: Validate data quality with built-in testing framework
4. **Documentation**: Auto-generate documentation for your data models
5. **Dependency Management**: Automatically handle model dependencies

## 🔄 The DuckDB + dbt Workflow

The combination of DuckDB and dbt creates a powerful, efficient analytics workflow:

1. **Raw Data Storage**: Store raw data in DuckDB's efficient columnar format
2. **Transformation**: Use dbt to transform raw data into analytics-ready models
3. **Testing**: Validate data quality with dbt tests
4. **Documentation**: Generate comprehensive documentation
5. **Analysis**: Query the transformed data for insights

## 🛠️ Setting Up Your Environment

Let's get started with setting up your environment:

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd vyaparbazaar_analytics
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up DuckDB and Run the Pipeline**:
   ```bash
   python run_pipeline.py
   ```

5. **Verify Setup**:
   ```bash
   cd dbt_project
   dbt debug
   ```

## 📂 Project Structure

The VyaparBazaar Analytics project follows a well-organized structure:

```
vyaparbazaar_analytics/
├── data/
│   ├── raw/                  # Raw data files
│   ├── transformed/          # Transformed data files
│   └── vyaparbazaar.duckdb   # DuckDB database
├── dbt_project/
│   ├── models/               # SQL models organized by layer
│   │   ├── staging/          # Basic cleaned versions of source tables
│   │   ├── intermediate/     # Transformed and joined models
│   │   ├── marts/            # Business-specific models
│   │   └── ml_features/      # ML-ready feature models
│   ├── macros/               # Reusable SQL snippets
│   ├── tests/                # Data quality tests
│   ├── seeds/                # Static data files
│   ├── dbt_project.yml       # Project configuration
│   └── profiles.yml          # Connection profiles
```

## 🧩 Core dbt Concepts

### Models

**Models** are SQL files that transform your data. They are organized in layers:

1. **Staging Models**: Clean, rename, and cast raw data
2. **Intermediate Models**: Join and transform staging models
3. **Mart Models**: Business-specific models for analysis
4. **ML Feature Models**: Prepare data for machine learning

### Sources

**Sources** define the raw data tables in your database:

```yaml
sources:
  - name: vyaparbazaar_raw
    description: "Raw data from VyaparBazaar e-commerce platform"
    tables:
      - name: vyaparbazaar_customers
        description: "Customer information"
```

### References

**References** allow models to depend on other models:

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
)
```

### Macros

**Macros** are reusable SQL snippets that can be used across multiple models:

```sql
{% macro date_diff_in_days(start_date, end_date) %}
    datediff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

-- Usage in a model
SELECT
    customer_id,
    {{ date_diff_in_days('first_order_date', 'last_order_date') }} as days_between_orders
FROM customer_orders
```

### Tests

**Tests** validate your data quality:

```yaml
models:
  - name: stg_customers
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
```

### Seeds

**Seeds** are CSV files that can be loaded into the database and used in models:

```sql
-- Reference a seed in a model
SELECT
    c.customer_id,
    c.customer_state,
    s.region,
    s.official_language
FROM {{ ref('stg_customers') }} c
LEFT JOIN {{ ref('indian_states') }} s ON c.customer_state = s.state_code
```

## 🚀 Your First dbt Commands

Let's run some basic dbt commands:

1. **Compile Models**:
   ```bash
   dbt compile
   ```

2. **Run Models**:
   ```bash
   dbt run
   ```

3. **Test Models**:
   ```bash
   dbt test
   ```

4. **Generate Documentation**:
   ```bash
   dbt docs generate
   dbt docs serve
   ```

## 🧪 Hands-on Exercises

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

## 📚 Additional Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [dbt Documentation](https://docs.getdbt.com/)
- [Analytics Engineering Cookbook](https://www.getdbt.com/analytics-engineering/cookbook/)
- [Modern Data Stack Blog](https://www.moderndatastack.xyz/)

## 🎯 Next Steps

In the next module, we'll dive deeper into data transformation fundamentals, including SQL basics in dbt, Jinja templating, and testing.

Happy modeling!

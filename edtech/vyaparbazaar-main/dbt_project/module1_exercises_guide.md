# Module 1: Hands-on Exercises Guide

This guide provides step-by-step instructions for completing the hands-on exercises in Module 1 of the VyaparBazaar Analytics Internship Camp.

## Prerequisites

Before starting the exercises, make sure you have:

1. Completed the setup steps in the [Intern Setup Guide](intern_setup_guide.md)
2. Successfully run the pipeline with `python run_pipeline.py`
3. Verified that dbt can connect to DuckDB with `dbt debug`

## Exercise 1.1: Project Exploration

### Objective

Gain a thorough understanding of the project structure, model organization, and dbt compilation process.

### Step 1: Examine the project structure

1. Open the project in your code editor
2. Navigate through the directory structure
3. Pay special attention to the following directories:
   - `models/staging/`: Contains basic cleaned versions of source tables
   - `models/intermediate/`: Contains transformed and joined models
   - `models/marts/`: Contains business-specific models
   - `models/ml_features/`: Contains ML-ready feature models

4. Open a few SQL files from each directory to understand their purpose and complexity

### Step 2: Run `dbt deps` to install dependencies

1. Open a terminal
2. Navigate to the `dbt_project` directory
3. Run the following command:
   ```bash
   dbt deps
   ```
4. Observe the output to see which packages are being installed

### Step 3: Run `dbt compile` to compile the models

1. In the same terminal, run:
   ```bash
   dbt compile
   ```
2. Observe the output to see which models are being compiled
3. Note the order in which models are compiled (this reflects dependencies)

### Step 4: Explore the compiled SQL in the target directory

1. Navigate to the `target/compiled/vyaparbazaar/models/` directory
2. Open several compiled SQL files from different model layers
3. Compare the original SQL files with their compiled versions
4. Pay attention to how dbt has resolved:
   - Model references (`{{ ref('model_name') }}`)
   - Source references (`{{ source('source_name', 'table_name') }}`)
   - Macros and Jinja templating

### Questions to Consider

1. How does dbt organize models into layers?
2. What's the difference between the original SQL and the compiled SQL?
3. How does dbt resolve references between models?
4. What naming conventions are used in the project?

## Exercise 1.2: Understanding Model Dependencies

### Objective

Understand how models depend on each other and visualize the data flow through the project.

### Step 1: Use `dbt docs serve` to view the documentation

1. In the terminal, run:
   ```bash
   dbt docs generate
   dbt docs serve --port 8081
   ```
2. Open a web browser and navigate to http://localhost:8081
3. Explore the documentation interface:
   - Model list
   - Source list
   - Database tab
   - Lineage Graph tab

### Step 2: Explore the lineage graph

1. Click on the "Lineage Graph" tab
2. Use the search box to filter models
3. Click on different models to see their details
4. Use the zoom and pan controls to navigate the graph
5. Observe how models are connected through references

### Step 3: Identify the dependencies of the `int_customer_behavior` model

1. In the lineage graph, search for "int_customer_behavior"
2. Click on the model to see its details
3. Note the models that feed into it (upstream dependencies)
4. Note the models that use it (downstream dependencies)
5. Click on each dependency to understand its purpose

### Step 4: Draw a simple diagram of the data flow

1. Using pen and paper or a digital drawing tool, create a diagram showing:
   - Source tables
   - Staging models
   - The `int_customer_behavior` intermediate model
   - Any downstream mart or ML feature models
2. Use arrows to indicate data flow
3. Label each component with its name and purpose

### Questions to Consider

1. How many layers of transformation does data go through?
2. What are the key source tables for customer behavior analysis?
3. How does the `int_customer_behavior` model contribute to downstream analytics?
4. What would happen if you changed a staging model that feeds into `int_customer_behavior`?

## Bonus Challenges

### Bonus 1: Explore the dbt project configuration

1. Open the `dbt_project.yml` file
2. Identify the model materialization settings for each layer
3. Understand why different materializations are used for different layers

### Bonus 2: Investigate the profiles configuration

1. Open the `profiles.yml` file
2. Understand how dbt connects to DuckDB
3. Identify any configuration options specific to DuckDB

### Bonus 3: Explore macros and tests

1. Navigate to the `macros/` directory and examine the available macros
2. Open the `date_utils.sql` and `string_utils.sql` files
3. Try to understand how these macros can be used in models
4. Navigate to the `tests/` directory and examine the custom tests
5. Think about how these tests can be applied to models

### Bonus 4: Explore seeds

1. Navigate to the `seeds/` directory and examine the CSV files
2. Run the following command to load the seeds into the database:
   ```bash
   dbt seed
   ```
3. Query the seed tables in DuckDB to see their contents
4. Think about how these seeds can be used in models

### Bonus 5: Run a specific model

1. Choose a model from the intermediate or mart layer
2. Run it using the following command:
   ```bash
   dbt run -m model_name
   ```
3. Observe the execution time and any dependencies that are also run

### Bonus 6: Explore the DuckDB database directly

1. Use Python to connect to the DuckDB database:
   ```python
   import duckdb
   con = duckdb.connect('../data/vyaparbazaar.duckdb')

   # List all tables
   tables = con.execute("SHOW TABLES").fetchall()
   for table in tables:
       print(table[0])

   # Query a specific table
   result = con.execute("SELECT * FROM vyaparbazaar_customers LIMIT 5").fetchdf()
   print(result)
   ```
2. Compare the raw tables with the transformed models

## Submission

After completing the exercises, prepare a brief summary of your findings:

1. Key observations about the project structure
2. A description of the data flow through the `int_customer_behavior` model
3. Your diagram of the data flow
4. Any challenges you encountered and how you resolved them

## Next Steps

After completing these exercises, you'll be ready to move on to Module 2, where you'll learn about data transformation fundamentals and create your own models.

## Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [SQL Tutorial](https://www.w3schools.com/sql/)
- [Markdown Guide](https://www.markdownguide.org/basic-syntax/) (for documentation)

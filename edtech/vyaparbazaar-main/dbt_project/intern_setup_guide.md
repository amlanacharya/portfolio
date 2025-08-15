# VyaparBazaar Analytics Internship Camp Setup Guide

Welcome to the VyaparBazaar Analytics Internship Camp! This guide will help you set up your development environment and get started with the project.

## Prerequisites

Before you begin, make sure you have the following installed on your computer:

- Python 3.8 or higher
- Git
- A code editor (VS Code recommended)

## Setup Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vyaparbazaar_analytics
```

### 2. Create a Virtual Environment

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up DuckDB

The project uses DuckDB as the database. The setup script will download the necessary data and create the database.

```bash
python run_pipeline.py
```

This script will:
1. Download the dataset
2. Transform it into VyaparBazaar format
3. Generate additional synthetic data
4. Load data into DuckDB
5. Run dbt models

> Note: This may take a few minutes to complete.

### 5. Verify Setup

To verify that everything is set up correctly:

```bash
cd dbt_project
dbt debug
```

You should see a success message indicating that dbt can connect to the database.

### 6. Generate and View Documentation

```bash
dbt docs generate
dbt docs serve --port 8081
```

This will start a web server at http://localhost:8081 where you can view the project documentation.

## Project Structure

- `data/`: Contains the DuckDB database and raw data files
- `dbt_project/`: Contains the dbt project
  - `models/`: SQL models organized by layer
    - `staging/`: Basic cleaned versions of source tables
    - `intermediate/`: Transformed and joined models
    - `marts/`: Business-specific models
    - `ml_features/`: ML-ready feature models
  - `macros/`: Reusable SQL snippets
  - `tests/`: Data quality tests
  - `seeds/`: Static data files
  - `dbt_project.yml`: Project configuration
  - `profiles.yml`: Connection profiles

## Common Commands

- `dbt run`: Run all models
- `dbt run -m model_name`: Run a specific model
- `dbt test`: Run all tests
- `dbt test -m model_name`: Test a specific model
- `dbt docs generate`: Generate documentation
- `dbt docs serve --port 8081`: Serve documentation on port 8081

## Troubleshooting

### Port Issues with dbt docs serve

If you encounter a port error when running `dbt docs serve`, try specifying a different port:

```bash
dbt docs serve --port 8081
```

### DuckDB Connection Issues

If you have issues connecting to DuckDB, verify that the path in `profiles.yml` is correct:

```yaml
vyaparbazaar:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: '../data/vyaparbazaar.duckdb'
```

### Python Environment Issues

If you encounter Python-related errors, make sure your virtual environment is activated and all dependencies are installed:

```bash
pip install -r requirements.txt
```

## Getting Help

If you encounter any issues during setup, please reach out to the camp instructors for assistance.

Happy modeling!

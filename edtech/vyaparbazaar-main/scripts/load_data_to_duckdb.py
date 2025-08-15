"""
Script to load the transformed VyaparBazaar data into DuckDB.
"""

import os
import duckdb
import glob
import pandas as pd

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFORMED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'transformed')
DUCKDB_PATH = os.path.join(BASE_DIR, 'data', 'vyaparbazaar.duckdb')

def load_data_to_duckdb():
    """Load all transformed CSV files into DuckDB"""
    print(f"Loading data into DuckDB at {DUCKDB_PATH}...")
    
    # Connect to DuckDB
    con = duckdb.connect(DUCKDB_PATH)
    
    # Get all CSV files in the transformed data directory
    csv_files = glob.glob(os.path.join(TRANSFORMED_DATA_DIR, '*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {TRANSFORMED_DATA_DIR}")
        return
    
    # Load each CSV file into a DuckDB table
    for csv_file in csv_files:
        table_name = os.path.basename(csv_file).replace('.csv', '')
        print(f"Loading {table_name}...")
        
        # Create table and load data
        con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{csv_file}', header=True, sample_size=1000);")
        
        # Verify data was loaded
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {count} rows into {table_name}")
    
    # List all tables
    tables = con.execute("SHOW TABLES").fetchall()
    print("\nTables in DuckDB:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Close connection
    con.close()
    
    print("\nData loading completed successfully!")

def main():
    """Main function to load data into DuckDB"""
    # Check if transformed data directory exists
    if not os.path.exists(TRANSFORMED_DATA_DIR):
        print(f"Error: Transformed data directory not found at {TRANSFORMED_DATA_DIR}")
        print("Please run the transform_to_vyaparbazaar.py and generate_synthetic_data.py scripts first.")
        return
    
    # Check if any CSV files exist
    csv_files = glob.glob(os.path.join(TRANSFORMED_DATA_DIR, '*.csv'))
    if not csv_files:
        print(f"Error: No CSV files found in {TRANSFORMED_DATA_DIR}")
        print("Please run the transform_to_vyaparbazaar.py and generate_synthetic_data.py scripts first.")
        return
    
    # Load data into DuckDB
    load_data_to_duckdb()

if __name__ == "__main__":
    main()

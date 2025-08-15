"""
Script to run the entire VyaparBazaar analytics pipeline:
1. Download the OLIST dataset
2. Transform it into VyaparBazaar data
3. Generate additional synthetic data
4. Load data into DuckDB
5. Run dbt models
"""

import os
import subprocess
import sys
import time

def run_command(command, description):
    """Run a command and print its output"""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"{'='*80}\n")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            shell=True
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode != 0:
            print(f"\nError: {description} failed with return code {process.returncode}")
            return False
        
        print(f"\n{description} completed successfully!")
        return True
    
    except Exception as e:
        print(f"\nError executing {description}: {str(e)}")
        return False

def main():
    """Main function to run the entire pipeline"""
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    scripts_dir = os.path.join(base_dir, 'scripts')
    dbt_dir = os.path.join(base_dir, 'dbt_project')
    
    # Step 1: Download the OLIST dataset
    if not run_command(
        f"python {os.path.join(scripts_dir, 'download_data.py')}",
        "Downloading OLIST dataset"
    ):
        print("Pipeline stopped due to error in data download step.")
        return
    
    # Step 2: Transform data into VyaparBazaar format
    if not run_command(
        f"python {os.path.join(scripts_dir, 'transform_to_vyaparbazaar.py')}",
        "Transforming data to VyaparBazaar format"
    ):
        print("Pipeline stopped due to error in data transformation step.")
        return
    
    # Step 3: Generate additional synthetic data
    if not run_command(
        f"python {os.path.join(scripts_dir, 'generate_synthetic_data.py')}",
        "Generating synthetic data"
    ):
        print("Pipeline stopped due to error in synthetic data generation step.")
        return
    
    # Step 4: Load data into DuckDB
    if not run_command(
        f"python {os.path.join(scripts_dir, 'load_data_to_duckdb.py')}",
        "Loading data into DuckDB"
    ):
        print("Pipeline stopped due to error in DuckDB data loading step.")
        return
    
    # Step 5: Run dbt models
    os.chdir(dbt_dir)
    if not run_command(
        "dbt run",
        "Running dbt models"
    ):
        print("Pipeline stopped due to error in dbt model execution step.")
        return
    
    # Step 6: Generate dbt documentation
    if not run_command(
        "dbt docs generate",
        "Generating dbt documentation"
    ):
        print("Warning: Could not generate dbt documentation, but pipeline completed.")
    
    print("\n\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + " " * 25 + "PIPELINE COMPLETED SUCCESSFULLY!" + " " * 25 + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")
    print("You can now explore the data in DuckDB and the transformed models.")
    print("To serve the dbt documentation, run: dbt docs serve")

if __name__ == "__main__":
    main()

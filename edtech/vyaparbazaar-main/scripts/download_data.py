"""
Script to download the OLIST Brazilian E-commerce dataset from Kaggle.
This will be our base dataset that we'll transform into the VyaparBazaar dataset.
"""

import os
import zipfile
import subprocess
import sys

def download_olist_dataset():
    """
    Download the OLIST dataset from Kaggle using the Kaggle API.
    Requires Kaggle API credentials to be set up.
    """
    print("Downloading OLIST Brazilian E-commerce dataset from Kaggle...")
    
    # Create raw data directory if it doesn't exist
    raw_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')
    os.makedirs(raw_data_dir, exist_ok=True)
    
    try:
        # Download the dataset using Kaggle API
        subprocess.run(
            ['kaggle', 'datasets', 'download', 'olistbr/brazilian-ecommerce', '-p', raw_data_dir],
            check=True
        )
        
        # Unzip the downloaded file
        zip_path = os.path.join(raw_data_dir, 'brazilian-ecommerce.zip')
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(raw_data_dir)
            print(f"Dataset extracted to {raw_data_dir}")
            
            # Remove the zip file after extraction
            os.remove(zip_path)
            print("Zip file removed")
        else:
            print(f"Zip file not found at {zip_path}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error downloading dataset: {e}")
        print("\nMake sure you have set up your Kaggle API credentials:")
        print("1. Go to https://www.kaggle.com/account")
        print("2. Create a new API token")
        print("3. Save the kaggle.json file to ~/.kaggle/kaggle.json")
        print("4. Ensure the file has permissions 600 (chmod 600 ~/.kaggle/kaggle.json)")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
        
    print("Download completed successfully!")

if __name__ == "__main__":
    download_olist_dataset()

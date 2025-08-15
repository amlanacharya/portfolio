"""
Script to transform the OLIST Brazilian E-commerce dataset into the VyaparBazaar Indian E-commerce dataset.
This transformation includes:
1. Converting Brazilian locations to Indian cities and states
2. Transforming product categories to match Indian market
3. Adjusting customer data to reflect Indian demographics
4. Modifying payment methods to Indian options
5. Adjusting dates to more recent timeframes
"""

import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import re

# Set up Faker for generating Indian data
fake_india = Faker('en_IN')
Faker.seed(42)  # For reproducibility
random.seed(42)
np.random.seed(42)

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
TRANSFORMED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'transformed')

# Ensure transformed directory exists
os.makedirs(TRANSFORMED_DATA_DIR, exist_ok=True)

# Indian states and major cities mapping
INDIAN_STATES = [
    'Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Telangana', 
    'Gujarat', 'Uttar Pradesh', 'West Bengal', 'Rajasthan', 'Kerala',
    'Haryana', 'Madhya Pradesh', 'Punjab', 'Bihar', 'Andhra Pradesh',
    'Odisha', 'Assam', 'Jharkhand', 'Uttarakhand', 'Chhattisgarh',
    'Himachal Pradesh', 'Goa', 'Tripura', 'Manipur', 'Meghalaya'
]

MAJOR_CITIES = {
    'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik'],
    'Delhi': ['New Delhi', 'Delhi', 'Noida', 'Gurgaon', 'Faridabad'],
    'Karnataka': ['Bangalore', 'Mysore', 'Hubli', 'Mangalore', 'Belgaum'],
    'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem'],
    'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar', 'Khammam'],
    'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Gandhinagar'],
    'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Meerut'],
    'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri'],
    'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer'],
    'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam']
}

# For states not in the major cities list, add generic cities
for state in INDIAN_STATES:
    if state not in MAJOR_CITIES:
        MAJOR_CITIES[state] = [f"{state} City", f"{state} Town", f"{state} Nagar"]

# Product category mapping (Brazilian to Indian context)
CATEGORY_MAPPING = {
    'cama_mesa_banho': 'home_furnishing',
    'beleza_saude': 'beauty_personal_care',
    'esporte_lazer': 'sports_fitness',
    'moveis_decoracao': 'furniture_decor',
    'informatica_acessorios': 'computers_accessories',
    'utilidades_domesticas': 'home_kitchen',
    'relogios_presentes': 'watches_gifts',
    'telefonia': 'mobile_phones',
    'automotivo': 'automotive',
    'brinquedos': 'toys_games',
    'cool_stuff': 'gadgets_electronics',
    'perfumaria': 'fragrances',
    'bebes': 'baby_products',
    'eletronicos': 'electronics',
    'papelaria': 'stationery',
    'fashion_bolsas_e_acessorios': 'fashion_bags_accessories',
    'fashion_calcados': 'footwear',
    'fashion_roupa_feminina': 'womens_clothing',
    'fashion_roupa_masculina': 'mens_clothing',
    'fashion_underwear_e_moda_praia': 'lingerie_sleepwear',
    'fashion_esporte': 'sportswear',
    'flores': 'flowers_gifts',
    'alimentos': 'grocery_gourmet',
    'alimentos_bebidas': 'food_beverages',
    'casa_conforto': 'home_improvement',
    'casa_conforto_2': 'home_appliances',
    'construcao_ferramentas_construcao': 'tools_hardware',
    'construcao_ferramentas_jardim': 'garden_outdoor',
    'construcao_ferramentas_seguranca': 'safety_tools',
    'ferramentas_jardim': 'gardening_tools',
    'industria_comercio_e_negocios': 'business_industrial',
    'livros_interesse_geral': 'books_general',
    'livros_tecnicos': 'books_technical',
    'musica': 'music_instruments',
    'pet_shop': 'pet_supplies',
    'artes': 'arts_crafts',
    'malas_acessorios': 'luggage_travel',
    'climatizacao': 'air_conditioning',
    'consoles_games': 'gaming_consoles',
    'dvds_blu_ray': 'movies_tv_shows',
    'eletrodomesticos': 'appliances',
    'eletrodomesticos_2': 'kitchen_appliances',
    'eletroportateis': 'small_appliances',
    'artigos_de_festas': 'party_supplies',
    'artigos_de_natal': 'festival_decorations',
    'audio': 'audio_devices',
    'market_place': 'marketplace_items',
    'portateis_casa_forno_e_cafe': 'kitchen_dining',
    'cine_foto': 'cameras_photography',
    'tablets_impressao_imagem': 'tablets_printers',
    'telefonia_fixa': 'landline_phones',
    'pcs': 'desktop_computers',
    'sinalizacao_e_seguranca': 'safety_security'
}

# Indian payment methods
INDIAN_PAYMENT_METHODS = [
    'UPI', 'credit_card', 'debit_card', 'net_banking', 'wallet', 'cash_on_delivery', 
    'EMI', 'gift_card', 'pay_later'
]

# Payment method distribution (probability weights)
PAYMENT_METHOD_WEIGHTS = [0.35, 0.15, 0.15, 0.1, 0.1, 0.1, 0.02, 0.02, 0.01]

# Indian festivals for sales spikes
INDIAN_FESTIVALS = {
    '2021': {
        'Diwali': '2021-11-04',
        'Holi': '2021-03-29',
        'Raksha Bandhan': '2021-08-22',
        'Durga Puja': '2021-10-11',
        'Christmas': '2021-12-25',
        'New Year': '2021-01-01',
        'Independence Day': '2021-08-15',
        'Republic Day': '2021-01-26'
    },
    '2022': {
        'Diwali': '2022-10-24',
        'Holi': '2022-03-18',
        'Raksha Bandhan': '2022-08-11',
        'Durga Puja': '2022-10-01',
        'Christmas': '2022-12-25',
        'New Year': '2022-01-01',
        'Independence Day': '2022-08-15',
        'Republic Day': '2022-01-26'
    },
    '2023': {
        'Diwali': '2023-11-12',
        'Holi': '2023-03-08',
        'Raksha Bandhan': '2023-08-30',
        'Durga Puja': '2023-10-20',
        'Christmas': '2023-12-25',
        'New Year': '2023-01-01',
        'Independence Day': '2023-08-15',
        'Republic Day': '2023-01-26'
    }
}

def transform_customers(df_customers):
    """Transform customer data to Indian context"""
    print("Transforming customer data...")
    
    # Create a copy to avoid modifying the original
    df = df_customers.copy()
    
    # Generate Indian customer data
    indian_customers = []
    
    for _, row in df.iterrows():
        state = random.choice(INDIAN_STATES)
        city = random.choice(MAJOR_CITIES[state])
        
        customer = {
            'customer_id': row['customer_id'],  # Keep original ID
            'customer_unique_id': row['customer_unique_id'],  # Keep original unique ID
            'customer_zip_code_prefix': fake_india.postcode(),
            'customer_city': city,
            'customer_state': state
        }
        indian_customers.append(customer)
    
    return pd.DataFrame(indian_customers)

def transform_orders(df_orders):
    """Transform order data to more recent timeframes and adjust for Indian context"""
    print("Transforming order data...")
    
    # Create a copy to avoid modifying the original
    df = df_orders.copy()
    
    # Define date range for transformation (2021-2023)
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    # Calculate the time span of the original dataset
    original_start = pd.to_datetime(df['order_purchase_timestamp']).min()
    original_end = pd.to_datetime(df['order_purchase_timestamp']).max()
    original_span = (original_end - original_start).days
    
    # Calculate the time span of our new date range
    new_span = (end_date - start_date).days
    
    # Function to map dates from original range to new range
    def map_date(original_date):
        original_date = pd.to_datetime(original_date)
        days_from_start = (original_date - original_start).days
        proportion = days_from_start / original_span if original_span > 0 else 0
        days_in_new_range = int(proportion * new_span)
        new_date = start_date + timedelta(days=days_in_new_range)
        
        # Add randomness to avoid exact mapping
        random_days = random.randint(-10, 10)
        new_date += timedelta(days=random_days)
        
        # Ensure date is within our range
        if new_date < start_date:
            new_date = start_date + timedelta(days=random.randint(0, 30))
        if new_date > end_date:
            new_date = end_date - timedelta(days=random.randint(0, 30))
            
        return new_date
    
    # Apply date transformation to all date columns
    date_columns = [
        'order_purchase_timestamp', 
        'order_approved_at', 
        'order_delivered_carrier_date', 
        'order_delivered_customer_date', 
        'order_estimated_delivery_date'
    ]
    
    for col in date_columns:
        df[col] = df[col].apply(lambda x: map_date(x) if pd.notna(x) else x)
    
    # Ensure logical order of dates
    for i, row in df.iterrows():
        purchase_date = row['order_purchase_timestamp']
        
        # Approved date should be after purchase date
        if pd.notna(row['order_approved_at']):
            approved_date = max(purchase_date, row['order_approved_at'])
            df.at[i, 'order_approved_at'] = approved_date
            
            # Add 0-2 days for approval
            df.at[i, 'order_approved_at'] = approved_date + timedelta(days=random.randint(0, 2))
        else:
            # If approved date is NaN, set it to purchase date + random days
            df.at[i, 'order_approved_at'] = purchase_date + timedelta(days=random.randint(0, 2))
        
        approved_date = df.at[i, 'order_approved_at']
        
        # Carrier date should be after approved date
        if pd.notna(row['order_delivered_carrier_date']):
            df.at[i, 'order_delivered_carrier_date'] = approved_date + timedelta(days=random.randint(1, 3))
        
        carrier_date = df.at[i, 'order_delivered_carrier_date'] if pd.notna(df.at[i, 'order_delivered_carrier_date']) else approved_date
        
        # Customer delivery date should be after carrier date
        if pd.notna(row['order_delivered_customer_date']):
            df.at[i, 'order_delivered_customer_date'] = carrier_date + timedelta(days=random.randint(1, 7))
        
        # Estimated delivery should be reasonable
        df.at[i, 'order_estimated_delivery_date'] = purchase_date + timedelta(days=random.randint(7, 15))
    
    return df

def transform_order_items(df_items):
    """Transform order items data"""
    print("Transforming order items data...")
    
    # Create a copy to avoid modifying the original
    df = df_items.copy()
    
    # Convert prices from BRL to INR (approximate conversion: 1 BRL = 15 INR)
    price_columns = ['price', 'freight_value']
    for col in price_columns:
        df[col] = df[col] * 15
        
        # Add some randomness to prices
        df[col] = df[col] * np.random.uniform(0.9, 1.1, size=len(df))
        
        # Round to 2 decimal places
        df[col] = df[col].round(2)
    
    return df

def transform_products(df_products):
    """Transform product data to Indian context"""
    print("Transforming product data...")
    
    # Create a copy to avoid modifying the original
    df = df_products.copy()
    
    # Map product categories
    df['product_category_name'] = df['product_category_name'].map(
        lambda x: CATEGORY_MAPPING.get(x, x) if pd.notna(x) else x
    )
    
    # Convert product dimensions from cm to inches and weights from g to kg where appropriate
    dimension_columns = ['product_length_cm', 'product_height_cm', 'product_width_cm']
    for col in dimension_columns:
        # Keep in cm but adjust values slightly
        df[col] = df[col] * np.random.uniform(0.9, 1.1, size=len(df))
        df[col] = df[col].round(2)
    
    # Weight in grams - keep as is but add randomness
    df['product_weight_g'] = df['product_weight_g'] * np.random.uniform(0.9, 1.1, size=len(df))
    df['product_weight_g'] = df['product_weight_g'].round(2)
    
    # Add Indian product name translations (for demonstration)
    df['product_category_name_english'] = df['product_category_name']
    
    return df

def transform_sellers(df_sellers):
    """Transform seller data to Indian context"""
    print("Transforming seller data...")
    
    # Create a copy to avoid modifying the original
    df = df_sellers.copy()
    
    # Generate Indian seller data
    indian_sellers = []
    
    for _, row in df.iterrows():
        state = random.choice(INDIAN_STATES)
        city = random.choice(MAJOR_CITIES[state])
        
        seller = {
            'seller_id': row['seller_id'],  # Keep original ID
            'seller_zip_code_prefix': fake_india.postcode(),
            'seller_city': city,
            'seller_state': state
        }
        indian_sellers.append(seller)
    
    return pd.DataFrame(indian_sellers)

def transform_payments(df_payments):
    """Transform payment data to Indian payment methods"""
    print("Transforming payment data...")
    
    # Create a copy to avoid modifying the original
    df = df_payments.copy()
    
    # Map payment types to Indian payment methods
    payment_mapping = {}
    unique_payment_types = df['payment_type'].unique()
    
    # Assign Indian payment methods to original payment types
    for payment_type in unique_payment_types:
        payment_mapping[payment_type] = np.random.choice(
            INDIAN_PAYMENT_METHODS, 
            p=PAYMENT_METHOD_WEIGHTS
        )
    
    # Apply mapping but also allow for some randomness
    df['payment_type'] = df.apply(
        lambda row: payment_mapping.get(row['payment_type'], 
                                       np.random.choice(INDIAN_PAYMENT_METHODS, p=PAYMENT_METHOD_WEIGHTS)),
        axis=1
    )
    
    # Convert values from BRL to INR
    df['payment_value'] = df['payment_value'] * 15
    
    # Add some randomness to payment values
    df['payment_value'] = df['payment_value'] * np.random.uniform(0.9, 1.1, size=len(df))
    
    # Round to 2 decimal places
    df['payment_value'] = df['payment_value'].round(2)
    
    # Adjust installments for Indian context (EMI is common in India)
    # For credit card and EMI payments, keep installments, for others set to 1
    df['payment_installments'] = df.apply(
        lambda row: row['payment_installments'] if row['payment_type'] in ['credit_card', 'EMI'] else 1,
        axis=1
    )
    
    return df

def transform_reviews(df_reviews):
    """Transform review data"""
    print("Transforming review data...")
    
    # Create a copy to avoid modifying the original
    df = df_reviews.copy()
    
    # Map review dates to our new timeframe
    # Define date range for transformation (2021-2023)
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    # Calculate the time span of the original dataset
    original_start = pd.to_datetime(df['review_creation_date']).min()
    original_end = pd.to_datetime(df['review_creation_date']).max()
    original_span = (original_end - original_start).days
    
    # Calculate the time span of our new date range
    new_span = (end_date - start_date).days
    
    # Function to map dates from original range to new range
    def map_date(original_date):
        original_date = pd.to_datetime(original_date)
        days_from_start = (original_date - original_start).days
        proportion = days_from_start / original_span if original_span > 0 else 0
        days_in_new_range = int(proportion * new_span)
        new_date = start_date + timedelta(days=days_in_new_range)
        
        # Add randomness to avoid exact mapping
        random_days = random.randint(-10, 10)
        new_date += timedelta(days=random_days)
        
        # Ensure date is within our range
        if new_date < start_date:
            new_date = start_date + timedelta(days=random.randint(0, 30))
        if new_date > end_date:
            new_date = end_date - timedelta(days=random.randint(0, 30))
            
        return new_date
    
    # Apply date transformation to date columns
    date_columns = ['review_creation_date', 'review_answer_timestamp']
    
    for col in date_columns:
        df[col] = df[col].apply(lambda x: map_date(x) if pd.notna(x) else x)
    
    # Ensure answer date is after creation date
    for i, row in df.iterrows():
        creation_date = row['review_creation_date']
        
        if pd.notna(row['review_answer_timestamp']):
            # Answer should be 0-3 days after creation
            df.at[i, 'review_answer_timestamp'] = creation_date + timedelta(days=random.randint(0, 3))
    
    return df

def main():
    """Main function to transform all datasets"""
    print("Starting data transformation process...")
    
    # Check if raw data files exist
    required_files = [
        'olist_customers_dataset.csv',
        'olist_orders_dataset.csv',
        'olist_order_items_dataset.csv',
        'olist_products_dataset.csv',
        'olist_sellers_dataset.csv',
        'olist_order_payments_dataset.csv',
        'olist_order_reviews_dataset.csv'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(RAW_DATA_DIR, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"Error: The following required files are missing: {', '.join(missing_files)}")
        print("Please run the download_data.py script first.")
        return
    
    # Load datasets
    df_customers = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_customers_dataset.csv'))
    df_orders = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_orders_dataset.csv'))
    df_items = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_order_items_dataset.csv'))
    df_products = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_products_dataset.csv'))
    df_sellers = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_sellers_dataset.csv'))
    df_payments = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_order_payments_dataset.csv'))
    df_reviews = pd.read_csv(os.path.join(RAW_DATA_DIR, 'olist_order_reviews_dataset.csv'))
    
    # Transform datasets
    df_customers_transformed = transform_customers(df_customers)
    df_orders_transformed = transform_orders(df_orders)
    df_items_transformed = transform_order_items(df_items)
    df_products_transformed = transform_products(df_products)
    df_sellers_transformed = transform_sellers(df_sellers)
    df_payments_transformed = transform_payments(df_payments)
    df_reviews_transformed = transform_reviews(df_reviews)
    
    # Save transformed datasets
    df_customers_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_customers.csv'), index=False)
    df_orders_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_orders.csv'), index=False)
    df_items_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_order_items.csv'), index=False)
    df_products_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_products.csv'), index=False)
    df_sellers_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_sellers.csv'), index=False)
    df_payments_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_payments.csv'), index=False)
    df_reviews_transformed.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_reviews.csv'), index=False)
    
    print("Transformation completed successfully!")
    print(f"Transformed data saved to: {TRANSFORMED_DATA_DIR}")

if __name__ == "__main__":
    main()

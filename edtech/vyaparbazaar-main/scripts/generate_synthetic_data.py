"""
Script to generate additional synthetic data for the VyaparBazaar dataset.
This includes:
1. Website clickstream data
2. Customer support interactions
3. Marketing campaign data
4. App usage data
"""

import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import json

# Set up Faker for generating Indian data
fake_india = Faker('en_IN')
Faker.seed(42)  # For reproducibility
random.seed(42)
np.random.seed(42)

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFORMED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'transformed')

# Ensure transformed directory exists
os.makedirs(TRANSFORMED_DATA_DIR, exist_ok=True)

# Define constants for synthetic data generation
PAGE_TYPES = [
    'home', 'category', 'product', 'search_results', 'cart', 'checkout', 
    'payment', 'order_confirmation', 'account', 'wishlist'
]

EVENTS = [
    'page_view', 'product_view', 'add_to_cart', 'remove_from_cart', 
    'add_to_wishlist', 'begin_checkout', 'purchase', 'search', 
    'apply_coupon', 'login', 'logout', 'register', 'view_promotion'
]

DEVICES = ['desktop', 'mobile_app', 'mobile_web', 'tablet']
BROWSERS = ['Chrome', 'Safari', 'Firefox', 'Edge', 'Opera', 'UC Browser']
OS = ['Windows', 'Android', 'iOS', 'MacOS', 'Linux']

SEARCH_TERMS = [
    'smartphone', 'laptop', 'headphones', 'saree', 'kurta', 'jeans', 
    'shoes', 'watch', 'tv', 'refrigerator', 'washing machine', 'camera',
    'bluetooth speaker', 'microwave oven', 'air conditioner', 'water purifier',
    'books', 'toys', 'baby products', 'groceries', 'furniture', 'kitchenware',
    'sports equipment', 'beauty products', 'jewelry', 'home decor'
]

SUPPORT_CATEGORIES = [
    'order_status', 'return_request', 'refund_status', 'product_inquiry',
    'payment_issue', 'delivery_delay', 'damaged_product', 'wrong_product',
    'account_issue', 'technical_problem', 'coupon_issue', 'general_inquiry'
]

SUPPORT_CHANNELS = ['phone', 'email', 'chat', 'social_media', 'app']
SUPPORT_STATUS = ['open', 'in_progress', 'resolved', 'closed', 'escalated']
SATISFACTION_LEVELS = [1, 2, 3, 4, 5]  # 1=Very Dissatisfied, 5=Very Satisfied

MARKETING_CHANNELS = [
    'email', 'sms', 'push_notification', 'social_media', 'search_ads',
    'display_ads', 'affiliate', 'influencer', 'tv', 'radio'
]

CAMPAIGN_TYPES = [
    'discount', 'flash_sale', 'new_arrival', 'seasonal', 'festival',
    'clearance', 'loyalty_program', 'referral', 'reactivation', 'brand_awareness'
]

APP_SCREENS = [
    'home', 'category_list', 'product_detail', 'search', 'cart',
    'checkout', 'payment', 'order_history', 'wishlist', 'account',
    'notifications', 'settings', 'reviews', 'recommendations'
]

APP_ACTIONS = [
    'screen_view', 'tap', 'scroll', 'swipe', 'pinch', 'long_press',
    'add_to_cart', 'purchase', 'search', 'filter', 'sort', 'share'
]

def load_transformed_data():
    """Load the transformed VyaparBazaar data"""
    customers = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_customers.csv'))
    orders = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_orders.csv'))
    products = pd.read_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_products.csv'))
    
    return customers, orders, products

def generate_clickstream_data(customers, orders, products, num_events=100000):
    """Generate website clickstream data"""
    print("Generating clickstream data...")
    
    clickstream_data = []
    
    # Get unique customer IDs and product IDs
    customer_ids = customers['customer_unique_id'].unique()
    product_ids = products['product_id'].unique()
    
    # Generate events
    for _ in range(num_events):
        customer_id = np.random.choice(customer_ids)
        
        # Generate timestamp between 2021-2023
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        days_between = (end_date - start_date).days
        random_day = random.randint(0, days_between)
        event_date = start_date + timedelta(days=random_day)
        
        # Add random hour, minute, second
        event_date = event_date.replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Generate event data
        event_type = np.random.choice(EVENTS, p=[0.3, 0.2, 0.1, 0.05, 0.05, 0.05, 0.05, 0.1, 0.02, 0.03, 0.02, 0.02, 0.01])
        page_type = np.random.choice(PAGE_TYPES)
        device = np.random.choice(DEVICES, p=[0.3, 0.4, 0.2, 0.1])
        
        # Device-specific details
        if device == 'desktop':
            browser = np.random.choice(BROWSERS, p=[0.5, 0.2, 0.15, 0.1, 0.03, 0.02])
            os = np.random.choice(['Windows', 'MacOS', 'Linux'], p=[0.7, 0.25, 0.05])
            app_version = None
        elif device in ['mobile_app', 'mobile_web', 'tablet']:
            browser = np.random.choice(BROWSERS, p=[0.4, 0.3, 0.1, 0.05, 0.05, 0.1]) if device != 'mobile_app' else None
            os = np.random.choice(['Android', 'iOS'], p=[0.7, 0.3])
            app_version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}" if device == 'mobile_app' else None
        
        # Event-specific details
        event_details = {}
        
        if event_type == 'product_view':
            event_details['product_id'] = np.random.choice(product_ids)
        elif event_type == 'add_to_cart':
            event_details['product_id'] = np.random.choice(product_ids)
            event_details['quantity'] = random.randint(1, 5)
        elif event_type == 'search':
            event_details['search_term'] = np.random.choice(SEARCH_TERMS)
            event_details['results_count'] = random.randint(0, 100)
        elif event_type == 'purchase':
            # Try to match with an actual order if possible
            customer_orders = orders[orders['customer_id'] == customer_id]
            if not customer_orders.empty:
                order_id = np.random.choice(customer_orders['order_id'].values)
                event_details['order_id'] = order_id
            else:
                event_details['order_id'] = f"order_{random.randint(10000, 99999)}"
            event_details['order_value'] = round(random.uniform(500, 10000), 2)
        
        # Create event record
        event = {
            'event_id': f"event_{len(clickstream_data) + 1}",
            'customer_id': customer_id,
            'event_timestamp': event_date.strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': event_type,
            'page_type': page_type,
            'device': device,
            'browser': browser,
            'operating_system': os,
            'app_version': app_version,
            'session_id': f"session_{random.randint(10000, 99999)}",
            'event_details': json.dumps(event_details)
        }
        
        clickstream_data.append(event)
    
    # Convert to DataFrame
    df_clickstream = pd.DataFrame(clickstream_data)
    
    return df_clickstream

def generate_support_data(customers, orders, num_tickets=10000):
    """Generate customer support interaction data"""
    print("Generating customer support data...")
    
    support_data = []
    
    # Get unique customer IDs and order IDs
    customer_ids = customers['customer_unique_id'].unique()
    order_ids = orders['order_id'].unique()
    
    # Generate support tickets
    for i in range(num_tickets):
        customer_id = np.random.choice(customer_ids)
        
        # 80% of tickets are related to orders
        if random.random() < 0.8:
            order_id = np.random.choice(order_ids)
        else:
            order_id = None
        
        # Generate timestamp between 2021-2023
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        days_between = (end_date - start_date).days
        random_day = random.randint(0, days_between)
        created_date = start_date + timedelta(days=random_day)
        
        # Add random hour, minute, second
        created_date = created_date.replace(
            hour=random.randint(8, 20),  # Business hours
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Generate ticket data
        category = np.random.choice(SUPPORT_CATEGORIES)
        channel = np.random.choice(SUPPORT_CHANNELS)
        status = np.random.choice(SUPPORT_STATUS)
        
        # Resolution time based on status
        if status in ['resolved', 'closed']:
            resolution_hours = random.randint(1, 72)
            resolved_date = created_date + timedelta(hours=resolution_hours)
            satisfaction = np.random.choice(SATISFACTION_LEVELS, p=[0.05, 0.1, 0.2, 0.4, 0.25])
        else:
            resolved_date = None
            satisfaction = None
        
        # Create support ticket record
        ticket = {
            'ticket_id': f"TICKET{i+10000}",
            'customer_id': customer_id,
            'order_id': order_id,
            'created_at': created_date.strftime('%Y-%m-%d %H:%M:%S'),
            'category': category,
            'channel': channel,
            'status': status,
            'resolved_at': resolved_date.strftime('%Y-%m-%d %H:%M:%S') if resolved_date else None,
            'satisfaction_rating': satisfaction,
            'priority': np.random.choice(['low', 'medium', 'high', 'urgent'], p=[0.3, 0.4, 0.2, 0.1])
        }
        
        support_data.append(ticket)
    
    # Convert to DataFrame
    df_support = pd.DataFrame(support_data)
    
    return df_support

def generate_marketing_data(num_campaigns=100):
    """Generate marketing campaign data"""
    print("Generating marketing campaign data...")
    
    campaign_data = []
    
    # Generate campaigns
    for i in range(num_campaigns):
        # Generate start date between 2021-2023
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        days_between = (end_date - start_date).days
        random_day = random.randint(0, days_between - 30)  # Ensure at least 30 days for campaign
        campaign_start = start_date + timedelta(days=random_day)
        
        # Campaign duration between 1-30 days
        duration_days = random.randint(1, 30)
        campaign_end = campaign_start + timedelta(days=duration_days)
        
        # Generate campaign data
        channel = np.random.choice(MARKETING_CHANNELS)
        campaign_type = np.random.choice(CAMPAIGN_TYPES)
        
        # Budget and performance metrics
        budget = round(random.uniform(10000, 1000000), 2)
        impressions = random.randint(1000, 1000000)
        clicks = int(impressions * random.uniform(0.01, 0.1))  # 1-10% CTR
        conversions = int(clicks * random.uniform(0.01, 0.05))  # 1-5% conversion rate
        revenue = round(conversions * random.uniform(1000, 5000), 2)
        
        # Create campaign record
        campaign = {
            'campaign_id': f"CAMP{i+1000}",
            'campaign_name': f"{campaign_type.title()} Campaign {i+1}",
            'channel': channel,
            'campaign_type': campaign_type,
            'start_date': campaign_start.strftime('%Y-%m-%d'),
            'end_date': campaign_end.strftime('%Y-%m-%d'),
            'budget': budget,
            'impressions': impressions,
            'clicks': clicks,
            'conversions': conversions,
            'revenue': revenue,
            'target_audience': np.random.choice(['new_customers', 'existing_customers', 'all'], p=[0.3, 0.3, 0.4]),
            'discount_percentage': random.randint(5, 50) if 'discount' in campaign_type else None
        }
        
        campaign_data.append(campaign)
    
    # Convert to DataFrame
    df_campaigns = pd.DataFrame(campaign_data)
    
    return df_campaigns

def generate_app_usage_data(customers, num_events=50000):
    """Generate mobile app usage data"""
    print("Generating app usage data...")
    
    app_data = []
    
    # Get unique customer IDs
    customer_ids = customers['customer_unique_id'].unique()
    
    # Generate app events
    for _ in range(num_events):
        customer_id = np.random.choice(customer_ids)
        
        # Generate timestamp between 2021-2023
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        days_between = (end_date - start_date).days
        random_day = random.randint(0, days_between)
        event_date = start_date + timedelta(days=random_day)
        
        # Add random hour, minute, second
        event_date = event_date.replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Generate event data
        screen = np.random.choice(APP_SCREENS)
        action = np.random.choice(APP_ACTIONS)
        os = np.random.choice(['Android', 'iOS'], p=[0.7, 0.3])
        app_version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
        
        # Create app event record
        event = {
            'event_id': f"app_event_{len(app_data) + 1}",
            'customer_id': customer_id,
            'event_timestamp': event_date.strftime('%Y-%m-%d %H:%M:%S'),
            'screen': screen,
            'action': action,
            'operating_system': os,
            'app_version': app_version,
            'session_id': f"app_session_{random.randint(10000, 99999)}",
            'duration_seconds': random.randint(1, 300),
            'device_model': f"{'iPhone' if os == 'iOS' else 'Samsung Galaxy'} {random.choice(['X', 'S', 'A', 'Note'])}{random.randint(1, 20)}"
        }
        
        app_data.append(event)
    
    # Convert to DataFrame
    df_app = pd.DataFrame(app_data)
    
    return df_app

def main():
    """Main function to generate all synthetic datasets"""
    print("Starting synthetic data generation process...")
    
    # Check if transformed data files exist
    required_files = [
        'vyaparbazaar_customers.csv',
        'vyaparbazaar_orders.csv',
        'vyaparbazaar_products.csv'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(TRANSFORMED_DATA_DIR, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"Error: The following required files are missing: {', '.join(missing_files)}")
        print("Please run the transform_to_vyaparbazaar.py script first.")
        return
    
    # Load transformed data
    customers, orders, products = load_transformed_data()
    
    # Generate synthetic datasets
    df_clickstream = generate_clickstream_data(customers, orders, products, num_events=50000)
    df_support = generate_support_data(customers, orders, num_tickets=5000)
    df_campaigns = generate_marketing_data(num_campaigns=50)
    df_app_usage = generate_app_usage_data(customers, num_events=30000)
    
    # Save synthetic datasets
    df_clickstream.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_clickstream.csv'), index=False)
    df_support.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_support_tickets.csv'), index=False)
    df_campaigns.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_marketing_campaigns.csv'), index=False)
    df_app_usage.to_csv(os.path.join(TRANSFORMED_DATA_DIR, 'vyaparbazaar_app_usage.csv'), index=False)
    
    print("Synthetic data generation completed successfully!")
    print(f"Synthetic data saved to: {TRANSFORMED_DATA_DIR}")

if __name__ == "__main__":
    main()

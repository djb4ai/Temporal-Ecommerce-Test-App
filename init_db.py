from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['ecommerce_db']

print("\nStarting database initialization...")

# Sample products
products = [
    {
        'sku': 'PROD001',
        'name': 'Laptop',
        'price': 999.99,
        'stock': 10,
        'description': 'High-performance laptop with 16GB RAM and 512GB SSD'
    },
    {
        'sku': 'PROD002',
        'name': 'Smartphone',
        'price': 699.99,
        'stock': 15,
        'description': 'Latest smartphone with 128GB storage'
    },
    {
        'sku': 'PROD003',
        'name': 'Headphones',
        'price': 199.99,
        'stock': 20,
        'description': 'Wireless noise-canceling headphones'
    },
    {
        'sku': 'PROD004',
        'name': 'Smartwatch',
        'price': 299.99,
        'stock': 8,
        'description': 'Fitness tracking smartwatch with heart rate monitor'
    },
    {
        'sku': 'PROD005',
        'name': 'Tablet',
        'price': 499.99,
        'stock': 12,
        'description': '10-inch tablet with 64GB storage'
    }
]

# Initialize collections
print("\nClearing existing collections...")

# Clear existing data
db.inventory.delete_many({})
print("- Cleared inventory collection")
db.balances.delete_many({})
print("- Cleared balances collection")
db.orders.delete_many({})
print("- Cleared orders collection")
db.rewards.delete_many({})
print("- Cleared rewards collection")

print("\nInitializing collections...")

# Insert sample products
db.inventory.insert_many(products)
print("- Added sample products")

# Initialize default user balance
default_balance = {
    'user_id': 'default_user',
    'balance': 2000.0,
    'created_at': datetime.now(),
    'updated_at': datetime.now(),
    'transactions': [{
        'amount': 2000.0,
        'type': 'initial_deposit',
        'timestamp': datetime.now()
    }]
}
result = db.balances.insert_one(default_balance)
print("- Added default user balance")

# Verify initialization
print("\nVerifying initialization...")
balance_doc = db.balances.find_one({'user_id': 'default_user'})
if balance_doc:
    print(f"- Default user balance verified: ${balance_doc.get('balance', 0.0):.2f}")
else:
    print("- ERROR: Default user balance not found!")

inventory_count = db.inventory.count_documents({})
print(f"- Inventory items count: {inventory_count}")

print("\nDatabase initialization complete!")
print("You can now start the application.") 
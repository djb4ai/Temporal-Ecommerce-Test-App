from temporalio import activity
from pymongo import MongoClient
import random
import time

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['ecommerce_db']
inventory = db['inventory']

@activity.defn
async def check_inventory(items: list) -> dict:
    # Simulate random failures (10% chance)
    if random.random() < 0.1:
        raise Exception("Inventory check failed")
    
    # Check each item's stock
    for item in items:
        stock_item = inventory.find_one({'sku': item['sku']})
        if not stock_item or stock_item['stock'] < item['quantity']:
            raise Exception(f"Insufficient stock for SKU {item['sku']}")
    
    # Simulate processing time
    time.sleep(1)
    
    return {
        "status": "success",
        "items_checked": len(items)
    }

@activity.defn
async def update_inventory(items: list) -> dict:
    # Update stock levels
    for item in items:
        inventory.update_one(
            {'sku': item['sku']},
            {'$inc': {'stock': -item['quantity']}}
        )
    
    return {
        "status": "success",
        "items_updated": len(items)
    } 
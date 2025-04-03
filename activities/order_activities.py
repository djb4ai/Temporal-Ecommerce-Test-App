from temporalio import activity
from pymongo import MongoClient
import os
from datetime import datetime

# MongoDB setup
mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = mongo_client['ecommerce_db']
orders = db['orders']

@activity.defn
async def update_order_status(order_id: str, status: str, details: dict = None) -> dict:
    """
    Update the status of an order in the database.
    
    Args:
        order_id: The ID of the order
        status: The new status (e.g., 'payment_processed', 'inventory_checked', 'shipping', 'completed')
        details: Optional additional details to store with the status update
    
    Returns:
        dict: The update result
    """
    # Create update document
    update_doc = {'status': status}
    
    # Add timestamp for the status change
    timestamp_field = f"{status}_at"
    update_doc[timestamp_field] = datetime.now()
    
    # Add any additional details if provided
    if details:
        for key, value in details.items():
            update_doc[key] = value
    
    # Update the order
    result = orders.update_one(
        {'order_id': order_id},
        {'$set': update_doc}
    )
    
    return {
        "status": "success" if result.modified_count > 0 else "not_found",
        "order_id": order_id,
        "new_status": status
    } 
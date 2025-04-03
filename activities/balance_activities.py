from temporalio import activity
from pymongo import MongoClient
import os
from datetime import datetime

# MongoDB setup
mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = mongo_client['ecommerce_db']
balances = db['balances']

@activity.defn
async def check_balance(user_id: str, amount: float) -> dict:
    """
    Check if user has sufficient balance for a transaction.
    
    Args:
        user_id: The ID of the user
        amount: The amount to check against the balance
    
    Returns:
        dict: Balance check result
    """
    # Get user's balance document
    balance_doc = balances.find_one({'user_id': user_id})
    
    if not balance_doc:
        raise Exception(f"No balance found for user {user_id}. Please initialize the database.")
    
    current_balance = balance_doc.get('balance', 0.0)
    has_sufficient = current_balance >= amount
    
    return {
        'status': 'sufficient' if has_sufficient else 'insufficient',
        'current_balance': current_balance,
        'required_amount': amount
    }

@activity.defn
async def update_balance(user_id: str, amount: float, transaction_type: str) -> dict:
    """
    Update user's balance after a transaction.
    
    Args:
        user_id: The ID of the user
        amount: The amount to deduct/add (negative for deduction, positive for addition)
        transaction_type: Type of transaction (e.g., 'payment', 'refund')
    
    Returns:
        dict: Update result
    """
    # Update balance with optimistic locking
    result = balances.find_one_and_update(
        {
            'user_id': user_id,
            'balance': {'$gte': -amount if amount < 0 else 0}  # Ensure sufficient balance for deductions
        },
        {
            '$inc': {'balance': amount},
            '$set': {'updated_at': datetime.now()},
            '$push': {
                'transactions': {
                    'amount': amount,
                    'type': transaction_type,
                    'timestamp': datetime.now()
                }
            }
        },
        return_document=True
    )
    
    if not result:
        raise Exception(f"Failed to update balance for user {user_id}. Insufficient funds or user not found.")
    
    return {
        'status': 'success',
        'new_balance': result['balance'],
        'transaction_amount': amount,
        'transaction_type': transaction_type
    } 
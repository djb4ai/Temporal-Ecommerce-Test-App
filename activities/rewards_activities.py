from temporalio import activity
from pymongo import MongoClient
import os
from datetime import datetime

# MongoDB setup
mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = mongo_client['ecommerce_db']
rewards = db['rewards']

@activity.defn
async def update_user_rewards(user_id: str, points_to_add: int) -> dict:
    """
    Update user rewards in MongoDB.
    Creates a new rewards document if user doesn't exist,
    or updates existing rewards by adding points.
    
    Args:
        user_id: The ID of the user
        points_to_add: Number of points to add to user's rewards
    
    Returns:
        dict: Updated rewards information
    """
    try:
        # Try to find existing rewards document
        result = rewards.find_one_and_update(
            {'user_id': user_id},
            {
                '$inc': {'total_points': points_to_add},
                '$push': {
                    'points_history': {
                        'points': points_to_add,
                        'timestamp': datetime.now(),
                        'type': 'order_purchase'
                    }
                },
                '$setOnInsert': {
                    'user_id': user_id,
                    'created_at': datetime.now()
                }
            },
            upsert=True,
            return_document=True
        )
        
        # Calculate reward tier based on total points
        total_points = result.get('total_points', points_to_add)
        tier = 'basic'
        if total_points >= 1000:
            tier = 'platinum'
        elif total_points >= 500:
            tier = 'gold'
        elif total_points >= 100:
            tier = 'silver'
            
        # Update tier if needed
        if result.get('tier', '').lower() != tier:
            rewards.update_one(
                {'user_id': user_id},
                {'$set': {'tier': tier}}
            )
        
        return {
            'status': 'success',
            'user_id': user_id,
            'total_points': total_points,
            'points_added': points_to_add,
            'current_tier': tier
        }
        
    except Exception as e:
        print(f"Error updating rewards: {str(e)}")
        raise 
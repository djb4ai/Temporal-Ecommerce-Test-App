from temporalio import activity
import random
import time

@activity.defn
async def send_notification(user_id: str, order_id: str, notification_type: str) -> dict:
    # Simulate random failures (10% chance)
    if random.random() < 0.1:
        raise Exception("Failed to send notification")
    
    # Simulate processing time
    time.sleep(1)
    
    # Log notification (in a real app, this would send email/SMS)
    print(f"Notification sent to user {user_id} for order {order_id}: {notification_type}")
    
    return {
        "status": "sent",
        "type": notification_type,
        "timestamp": time.time()
    }

@activity.defn
async def update_user_rewards(points: int, tier: str) -> dict:
    # Simulate random failures (5% chance)
    if random.random() < 0.05:
        raise Exception("Failed to update user rewards")
    
    # Simulate processing time
    time.sleep(0.5)
    
    # Log update (in a real app, this would update the database)
    print(f"Updated user rewards: points={points}, tier={tier}")
    
    return {
        "status": "updated",
        "points": points,
        "tier": tier
    } 
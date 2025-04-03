from temporalio import activity
import random
import time

@activity.defn
async def generate_shipping_label(item: dict) -> str:
    # Simulate random failures (15% chance)
    if random.random() < 0.15:
        raise Exception("Failed to generate shipping label")
    
    # Simulate processing time
    time.sleep(1)
    
    # Generate tracking number
    tracking_number = f"TRK{int(time.time())}{random.randint(1000, 9999)}"
    
    return tracking_number

@activity.defn
async def schedule_pickup(tracking_number: str) -> dict:
    # Simulate random failures (10% chance)
    if random.random() < 0.1:
        raise Exception("Failed to schedule pickup")
    
    # Simulate processing time
    time.sleep(1)
    
    return {
        "status": "scheduled",
        "tracking_number": tracking_number,
        "pickup_date": "2024-04-03"  # Simulated date
    }

@activity.defn
async def mark_delivered(tracking_number: str) -> dict:
    # Simulate random failures (5% chance)
    if random.random() < 0.05:
        raise Exception("Failed to mark as delivered")
    
    # Simulate processing time
    time.sleep(1)
    
    return {
        "status": "delivered",
        "tracking_number": tracking_number,
        "delivery_date": "2024-04-05"  # Simulated date
    } 
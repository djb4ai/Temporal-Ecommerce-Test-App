from temporalio import activity
import random
import time

@activity.defn
async def process_payment(user_id: str, order_id: str, items: list) -> dict:
    # Simulate payment processing
    total = sum(item['price'] * item['quantity'] for item in items)
    
    # Simulate random failures (20% chance)
    if random.random() < 0.2:
        raise Exception("Payment processing failed")
    
    # Simulate processing time
    time.sleep(1)
    
    return {
        "status": "success",
        "amount": total,
        "transaction_id": f"txn_{order_id}_{int(time.time())}"
    }

@activity.defn
async def refund_payment(user_id: str, order_id: str) -> dict:
    # Simulate refund processing
    time.sleep(1)
    
    return {
        "status": "refunded",
        "order_id": order_id
    } 
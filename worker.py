import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows.order_workflow import OrderProcessingWorkflow
from workflows.rewards_workflow import CustomerRewardsWorkflow
from workflows.shipping_workflow import ShippingWorkflow
from activities.payment_activities import process_payment, refund_payment
from activities.inventory_activities import check_inventory, update_inventory
from activities.shipping_activities import generate_shipping_label, schedule_pickup, mark_delivered
from activities.notification_activities import send_notification
from activities.order_activities import update_order_status
from activities.rewards_activities import update_user_rewards
from activities.balance_activities import check_balance, update_balance

async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")
    
    # Run a worker for the "ecommerce-task-queue" queue
    async with Worker(
        client,
        task_queue="ecommerce-task-queue",
        workflows=[
            OrderProcessingWorkflow,
            CustomerRewardsWorkflow,
            ShippingWorkflow
        ],
        activities=[
            process_payment,
            refund_payment,
            check_inventory,
            update_inventory,
            generate_shipping_label,
            schedule_pickup,
            mark_delivered,
            send_notification,
            update_order_status,
            update_user_rewards,
            check_balance,
            update_balance
        ]
    ):
        print("Worker started, listening on task queue 'ecommerce-task-queue'")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main()) 
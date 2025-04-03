from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
import random

@workflow.defn
class ShippingWorkflow:
    @workflow.run
    async def run(self, item: dict) -> dict:
        # Simulate shipping process with potential failures
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )
        
        # Define default activity options
        default_activity_options = {
            "schedule_to_close_timeout": timedelta(seconds=5),
            "retry_policy": retry_policy
        }
        
        try:
            # Generate shipping label
            label = await workflow.execute_activity(
                "generate_shipping_label",
                args=[item],
                **default_activity_options
            )
            
            # Simulate shipping delay
            await workflow.sleep(timedelta(seconds=2))
            
            # Schedule pickup
            pickup = await workflow.execute_activity(
                "schedule_pickup",
                args=[label],
                **default_activity_options
            )
            
            # Simulate transit time
            await workflow.sleep(timedelta(seconds=3))
            
            # Mark as delivered
            delivery = await workflow.execute_activity(
                "mark_delivered",
                args=[label],
                **default_activity_options
            )
            
            return {
                "status": "delivered",
                "tracking_number": label,
                "pickup_status": pickup,
                "delivery_status": delivery
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            } 
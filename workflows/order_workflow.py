from temporalio import workflow
from temporalio.workflow import ParentClosePolicy
from temporalio.common import RetryPolicy
from datetime import timedelta
import random
import asyncio
from dataclasses import dataclass
from workflows.rewards_workflow import CustomerRewardsWorkflow

@dataclass
class OrderRequest:
    user_id: str
    order_id: str
    items: list

@workflow.defn
class OrderProcessingWorkflow:
    @workflow.run
    async def process(self, request: OrderRequest) -> dict:
        # Set retry policy for activities
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
            # Update order status to processing
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "processing"],
                **default_activity_options
            )
            
            # Calculate total amount
            total_amount = sum(item['price'] * item['quantity'] for item in request.items)
            
            # Check balance before processing payment
            balance_check = await workflow.execute_activity(
                "check_balance",
                args=[request.user_id, total_amount],
                **default_activity_options
            )
            
            if balance_check['status'] != 'sufficient':
                raise Exception(f"Insufficient balance. Required: {total_amount}, Available: {balance_check['current_balance']}")
            
            # Process payment
            payment_activity_options = {
                "schedule_to_close_timeout": timedelta(seconds=10),
                "retry_policy": retry_policy
            }
            payment_result = await workflow.execute_activity(
                "process_payment",
                args=[request.user_id, request.order_id, request.items],
                **payment_activity_options
            )
            
            # Update balance after successful payment
            await workflow.execute_activity(
                "update_balance",
                args=[request.user_id, -total_amount, "payment"],
                **default_activity_options
            )
            
            # Update order status after payment
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "payment_processed", {"payment_details": payment_result}],
                **default_activity_options
            )
            
            # Check inventory
            inventory_result = await workflow.execute_activity(
                "check_inventory",
                args=[request.items],
                **default_activity_options
            )
            
            # Update order status after inventory check
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "inventory_checked", {"inventory_details": inventory_result}],
                **default_activity_options
            )
            
            # Update inventory levels
            await workflow.execute_activity(
                "update_inventory",
                args=[request.items],
                **default_activity_options
            )
            
            # Update order status after inventory update
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "inventory_updated"],
                **default_activity_options
            )
            
            # Update order status to shipping
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "shipping"],
                **default_activity_options
            )
            
            # Simulate shipping with child workflows
            shipping_tasks = []
            for item in request.items:
                shipping_tasks.append(
                    workflow.execute_child_workflow(
                        "ShippingWorkflow",
                        args=[item],
                        id=f"shipping_{request.order_id}_{item['sku']}"
                    )
                )
            
            # Wait for all shipping tasks to complete
            shipping_results = await asyncio.gather(*shipping_tasks)
            
            # Update order status after shipping
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "shipped", {"shipping_details": shipping_results}],
                **default_activity_options
            )
            
            # Send notification
            await workflow.execute_activity(
                "send_notification",
                args=[request.user_id, request.order_id, "order_shipped"],
                **default_activity_options
            )
            
            # Calculate points (1 point per dollar spent)
            total_points = int(sum(item['price'] * item['quantity'] for item in request.items))
            
            
            # Use a safer approach - always try to start the rewards workflow first
            # If it already exists, it will just return the existing one
            # I have used the workflow_id to get the existing workflow
            # and signal it with the points
            # If the workflow doesn't exist, it will start a new one
            # As the signal will fail
            try:
                rewards_id = f"rewards_{request.user_id}"

                try:
                    # Try to get existing workflow first
                    workflow_handle = workflow.get_external_workflow_handle(
                        #CustomerRewardsWorkflow,
                        workflow_id="rewards_default_user"
                    )
                    print("\n\n Before signal\n\n")
                    # Signal the rewards workflow with the points
                    await workflow_handle.signal("add_points", total_points)

                except Exception as e:
                    print(f"Exception in workflow try for rewards workflow: {e}")
                    # Workflow doesn't exist, start a new one  
                    workflow_handle = await workflow.start_child_workflow(
                        "CustomerRewardsWorkflow",
                        args=[request.user_id],
                        id=rewards_id,
                        # Unsure if this is the right way to do this
                        # I think it is because the rewards workflow is a child workflow
                        # and it should be abandoned if the parent workflow fails
                        # but I am not sure
                        parent_close_policy=ParentClosePolicy.ABANDON
                    )
                    # Send a notification that the rewards workflow has been started
                    await workflow.execute_activity(
                        "send_notification",
                        args=[request.user_id, request.order_id, "rewards_workflow_started"],
                        **default_activity_options
                    )
                    # Wait a moment for workflow to initialize
                    await asyncio.sleep(1)
                    # Signal the rewards workflow with the points
                    await workflow_handle.signal("add_points", total_points)
                
                # Update order status with rewards
                await workflow.execute_activity(
                    "update_order_status",
                    args=[request.order_id, "rewards_added", {"points_added": total_points}],
                    **default_activity_options
                )
            except Exception as e:
                # Log but don't fail the main workflow if rewards update fails
                print(f"Failed to update rewards: {str(e)}")
                # Continue without failing the order
                pass
            
            # Update order status to completed
            await workflow.execute_activity(
                "update_order_status",
                args=[request.order_id, "completed"],
                **default_activity_options
            )
            
            return {
                "status": "completed",
                "order_id": request.order_id,
                "payment_status": payment_result,
                "inventory_status": inventory_result,
                "shipping_status": shipping_results
            }
            
        except Exception as e:
            # Handle failures
            print(f"Order workflow encountered an error: {str(e)}")
            if "payment" in str(e) or "balance" in str(e):
                # Payment or balance check failed - no need to compensate
                # Update order status to failed
                try:
                    await workflow.execute_activity(
                        "update_order_status",
                        args=[request.order_id, "failed", {"reason": "payment_failed", "error": str(e)}],
                        **default_activity_options
                    )
                except Exception as update_error:
                    print(f"Failed to update order status: {str(update_error)}")
                
                return {"status": "failed", "reason": "payment_failed", "error": str(e)}
            elif "inventory" in str(e):
                # Inventory failed - refund payment and restore balance
                try:
                    # Calculate total amount for refund
                    total_amount = sum(item['price'] * item['quantity'] for item in request.items)
                    
                    # Refund payment
                    await workflow.execute_activity(
                        "refund_payment",
                        args=[request.user_id, request.order_id],
                        **default_activity_options
                    )
                    
                    # Restore balance
                    await workflow.execute_activity(
                        "update_balance",
                        args=[request.user_id, total_amount, "refund"],
                        **default_activity_options
                    )
                    
                    # Update order status to failed with refund
                    try:
                        await workflow.execute_activity(
                            "update_order_status",
                            args=[request.order_id, "failed", {"reason": "inventory_failed", "refund_status": "success", "error": str(e)}],
                            **default_activity_options
                        )
                    except Exception as update_error:
                        print(f"Failed to update order status: {str(update_error)}")
                    
                    return {"status": "failed", "reason": "inventory_failed", "error": str(e)}
                except Exception as refund_error:
                    print(f"Refund failed after inventory error: {str(refund_error)}")
                    
                    # Update order status to failed with failed refund
                    try:
                        await workflow.execute_activity(
                            "update_order_status",
                            args=[request.order_id, "failed", {
                                "reason": "inventory_failed_and_refund_failed", 
                                "error": str(e), 
                                "refund_error": str(refund_error)
                            }],
                            **default_activity_options
                        )
                    except Exception as update_error:
                        print(f"Failed to update order status: {str(update_error)}")
                    
                    return {"status": "failed", "reason": "inventory_failed_and_refund_failed", "error": str(e), "refund_error": str(refund_error)}
            else:
                # Other failures - attempt refund and restore balance
                print(f"Processing failed with error: {str(e)}")
                try:
                    # Calculate total amount for refund
                    total_amount = sum(item['price'] * item['quantity'] for item in request.items)
                    
                    # Refund payment
                    await workflow.execute_activity(
                        "refund_payment",
                        args=[request.user_id, request.order_id],
                        **default_activity_options
                    )
                    
                    # Restore balance
                    await workflow.execute_activity(
                        "update_balance",
                        args=[request.user_id, total_amount, "refund"],
                        **default_activity_options
                    )
                    
                    # Update order status to failed with refund
                    try:
                        await workflow.execute_activity(
                            "update_order_status",
                            args=[request.order_id, "failed", {"reason": "processing_failed", "refund_status": "success", "error": str(e)}],
                            **default_activity_options
                        )
                    except Exception as update_error:
                        print(f"Failed to update order status: {str(update_error)}")
                    
                    return {"status": "failed", "reason": "processing_failed", "error": str(e)}
                except Exception as refund_error:
                    print(f"Refund failed: {str(refund_error)}")
                    
                    # Update order status to failed with failed refund
                    try:
                        await workflow.execute_activity(
                            "update_order_status",
                            args=[request.order_id, "failed", {
                                "reason": "processing_failed_and_refund_failed", 
                                "error": str(e), 
                                "refund_error": str(refund_error)
                            }],
                            **default_activity_options
                        )
                    except Exception as update_error:
                        print(f"Failed to update order status: {str(update_error)}")
                    
                    return {"status": "failed", "reason": "processing_failed_and_refund_failed", "error": str(e), "refund_error": str(refund_error)}
                return {"status": "failed", "reason": "processing_failed", "error": str(e)} 
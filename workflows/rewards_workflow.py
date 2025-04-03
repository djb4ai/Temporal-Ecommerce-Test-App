from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

@workflow.defn
class CustomerRewardsWorkflow:
    def __init__(self):
        self._user_id = None
        self._initialized = False
        self.points = 0
        self._should_close = False  # Add flag for closing
        
    def _calculate_tier(self, total_points: int) -> str:
        """Calculate tier based on total points."""
        if total_points >= 1000:
            return "platinum"
        elif total_points >= 500:
            return "gold"
        elif total_points >= 100:
            return "silver"
        return "basic"
        
    @workflow.run
    async def run(self, user_id: str) -> dict:
        """Initialize the workflow with a user ID and rewards state."""
        # Initialize workflow state
        self._user_id = user_id
        self._initialized = True
        
        # Define activity options
        activity_options = {
            "schedule_to_close_timeout": timedelta(seconds=5),
            "retry_policy": RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3
            )
        }
        
        # Keep workflow running until close signal is received
        await workflow.wait_condition(lambda: self._should_close)
        return {
            "status": "completed",
            "user_id": user_id,
            "points": self.points,
            "tier": self._calculate_tier(self.points)
        }
    
    @workflow.signal
    async def add_points(self, points: int):
        """Signal handler to add points to user's rewards"""
        if not self._initialized or not self._user_id:
            raise ValueError("Workflow not properly initialized")
            
        # Set retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )
        
        # Define activity options
        activity_options = {
            "schedule_to_close_timeout": timedelta(seconds=5),
            "retry_policy": retry_policy
        }
        
        try:
            # Update points in workflow state
            self.points += points
            
            # Calculate current tier based on total points
            current_tier = self._calculate_tier(self.points)
            
            # Update rewards in MongoDB
            result = await workflow.execute_activity(
                "update_user_rewards",
                args=[self._user_id, self.points],
                **activity_options
            )
            
            # Send notification about rewards update
            # This notification is accessing the wrong information but the
            #final one is correct
            await workflow.execute_activity(
                "send_notification",
                args=[self._user_id, "rewards_updated", f"Added {points} points. New total: {self.points}. Tier: {current_tier}"],
                **activity_options
            )
            
            return result
        except Exception as e:
            print(f"Failed to update rewards: {str(e)}")
            raise
            
    @workflow.signal
    async def close_workflow(self):
        """Signal to gracefully close the workflow."""
        if not self._initialized or not self._user_id:
            raise ValueError("Workflow not properly initialized")
        
        self._should_close = True

    @workflow.query
    def get_user_id(self) -> str:
        """Query to get the current user ID."""
        return self._user_id if self._initialized else None

    @workflow.query
    def get_status(self) -> dict:
        """Query to get the current rewards status."""
        return {
            "points": self.points,
            "tier": self._calculate_tier(self.points)
        } 
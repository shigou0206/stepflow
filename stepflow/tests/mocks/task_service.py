
from stepflow.persistence.models import ActivityTask

class MockTaskService():

    async def create_task(self, run_id: str, state_name: str, activity_type: str, input_data: str) -> ActivityTask:
        return ActivityTask(
            run_id=run_id,
            state_name=state_name,
            activity_type=activity_type,
            input=input_data,
            status="scheduled"
        )

from typing import Optional, Dict, Any, List

class MockExecutionService:
    async def update_current_state(self, run_id: str, current_state_name: str) -> bool:
        return True

    async def update_context_snapshot(self, run_id: str, context: Dict[str, Any]) -> bool:
        return True

    async def complete_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return True

    async def fail_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return True

    async def cancel_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return True

    async def try_advance_state(self, run_id: str, next_state: str, expected_version: int) -> bool:
        return True

    async def get_execution(self, run_id: str):
        return None

    async def delete_workflow(self, run_id: str) -> bool:
        return True

    async def list_workflows(self) -> List[Any]:
        return []

    async def list_by_status(self, status: str) -> List[Any]:
        return []

    async def get_current_state(self, run_id: str) -> Optional[str]:
        return "DummyState"

    async def update_status(self, run_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        return None
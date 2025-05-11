import pytest
import json
from unittest.mock import AsyncMock, patch

from stepflow.persistence.models import ActivityTask
from stepflow.worker.activity_worker import process_single_task


@pytest.mark.asyncio
async def test_process_successful_task():
    task = ActivityTask(
        task_token="test-token",
        run_id="run-123",
        activity_type="MockTool",
        input=json.dumps({"foo": "bar"})
    )

    mock_tool = AsyncMock()
    mock_tool.execute.return_value = {"result": "done"}
    mock_service = AsyncMock()

    with patch.dict("stepflow.worker.activity_worker.tool_registry", {"MockTool": mock_tool}), \
         patch("stepflow.worker.activity_worker.advance_workflow", new=AsyncMock()):
        await process_single_task(task, mock_service)

    mock_service.start_task.assert_awaited_once_with(task.task_token)
    mock_service.complete_task.assert_awaited_once()
    mock_service.fail_task.assert_not_called()


@pytest.mark.asyncio
async def test_process_task_with_error_result():
    task = ActivityTask(
        task_token="test-token",
        run_id="run-456",
        activity_type="MockTool",
        input=json.dumps({"foo": "bar"})
    )

    mock_tool = AsyncMock()
    mock_tool.execute.return_value = {"error": "fail reason", "error_details": "stacktrace"}
    mock_service = AsyncMock()

    with patch.dict("stepflow.worker.activity_worker.tool_registry", {"MockTool": mock_tool}), \
         patch("stepflow.worker.activity_worker.advance_workflow", new=AsyncMock()):
        await process_single_task(task, mock_service)

    mock_service.fail_task.assert_awaited_once()
    mock_service.complete_task.assert_not_called()


@pytest.mark.asyncio
async def test_process_task_with_tool_not_found():
    task = ActivityTask(
        task_token="test-token",
        run_id="run-789",
        activity_type="UnknownTool",
        input="{}"
    )

    mock_service = AsyncMock()

    with patch.dict("stepflow.worker.activity_worker.tool_registry", {}), \
         patch("stepflow.worker.activity_worker.advance_workflow", new=AsyncMock()):
        await process_single_task(task, mock_service)

    mock_service.fail_task.assert_awaited_once()
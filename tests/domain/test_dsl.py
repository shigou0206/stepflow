import pytest
import pytest_asyncio
from pydantic import ValidationError
from stepflow.domain.dsl_model import WorkflowDSL

@pytest.mark.asyncio
async def test_valid_dsl_parsing():
    dsl_json = {
        "Version": "1.0",
        "Name": "OrderProcessingWorkflow",
        "Description": "Test DSL",
        "StartAt": "CheckInventory",
        "States": {
            "CheckInventory": {
                "Type": "Task",
                "ActivityType": "check_inventory",
                "Next": "ProcessPayment"
            },
            "ProcessPayment": {
                "Type": "Task",
                "ActivityType": "process_payment",
                "End": True
            }
        }
    }

    # 虽然这里没有实际IO，但我们保持异步test形式:
    workflow = WorkflowDSL(**dsl_json)
    assert workflow.Name == "OrderProcessingWorkflow"
    assert workflow.States["CheckInventory"].Type == "Task"
    assert workflow.States["ProcessPayment"].Type == "Task"
    assert workflow.States["ProcessPayment"].End is True

@pytest.mark.asyncio
async def test_invalid_dsl_parsing():
    invalid_json = {
        "Version": "1.0",
        "Name": "BrokenWorkflow",
        "StartAt": "DoesNotExist",
        "States": {
            "SomeState": {
                "Type": "NotAValidType"
            }
        }
    }

    with pytest.raises(ValidationError) as exc_info:
        # 这里也不需要 await, 但保留异步风格
        WorkflowDSL(**invalid_json)

    print("Caught ValidationError:", exc_info.value)
    assert "NotAValidType" in str(exc_info.value)
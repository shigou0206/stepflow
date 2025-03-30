# stepflow/interfaces/api/activity_endpoints.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from stepflow.infrastructure.database import SessionLocal
from stepflow.infrastructure.models import ActivityTask
from stepflow.domain.engine.execution_engine import advance_workflow
from datetime import datetime, UTC
import json

router = APIRouter(prefix="/activities", tags=["activities"])

class CompleteRequest(BaseModel):
    result: dict

@router.post("/{task_token}/complete")
def complete_activity(task_token: str, req: CompleteRequest, db: Session = Depends(SessionLocal)):
    act_task = db.query(ActivityTask).filter_by(task_token=task_token).one_or_none()
    if not act_task:
        return {"error": "Not found"}

    act_task.status = "completed"
    act_task.result = json.dumps(req.result)
    act_task.completed_at = datetime.now(UTC)
    db.commit()

    # now we can proceed workflow
    advance_workflow(db, act_task.run_id)
    return {"status": "ok"}

class FailRequest(BaseModel):
    reason: str

@router.post("/{task_token}/fail")
def fail_activity(task_token: str, req: FailRequest, db: Session = Depends(SessionLocal)):
    act_task = db.query(ActivityTask).filter_by(task_token=task_token).one_or_none()
    if not act_task:
        return {"error": "Not found"}

    act_task.status = "failed"
    act_task.result = req.reason
    act_task.completed_at = datetime.now(UTC)
    db.commit()

    advance_workflow(db, act_task.run_id)
    return {"status": "ok"}
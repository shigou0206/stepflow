from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, Union
from datetime import datetime
import json

# 工作流模板相关模式
class WorkflowTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    dsl_definition: str

class WorkflowTemplateCreate(WorkflowTemplateBase):
    template_id: Optional[str] = None

class WorkflowTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dsl_definition: Optional[str] = None

class WorkflowTemplateResponse(WorkflowTemplateBase):
    template_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# 工作流执行相关模式
class WorkflowExecutionCreate(BaseModel):
    workflow_id: str
    template_id: str
    input: Union[Dict[str, Any], str]  # 可以是JSON字符串或字典
    workflow_type: Optional[str] = None
    memo: Optional[str] = None
    search_attrs: Optional[Dict[str, Any]] = None

    def get_input_json(self) -> str:
        """获取输入的JSON字符串表示"""
        if isinstance(self.input, str):
            # 验证是否为有效的JSON
            try:
                json.loads(self.input)
                return self.input
            except json.JSONDecodeError:
                return json.dumps({"data": self.input})
        else:
            return json.dumps(self.input)

    def get_search_attrs_json(self) -> Optional[str]:
        """获取搜索属性的JSON字符串表示"""
        if self.search_attrs is None:
            return None
        if isinstance(self.search_attrs, str):
            # 验证是否为有效的JSON
            try:
                json.loads(self.search_attrs)
                return self.search_attrs
            except json.JSONDecodeError:
                return json.dumps({"data": self.search_attrs})
        else:
            return json.dumps(self.search_attrs)

class WorkflowExecutionResponse(BaseModel):
    run_id: str
    workflow_id: str
    template_id: str
    status: str
    current_state_name: Optional[str] = None
    workflow_type: str
    input: Optional[str] = None
    result: Optional[str] = None
    start_time: datetime
    close_time: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# 工作流可见性相关模式
class WorkflowVisibilityResponse(BaseModel):
    run_id: str
    workflow_id: Optional[str] = None
    workflow_type: Optional[str] = None
    start_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    status: Optional[str] = None
    memo: Optional[str] = None
    search_attrs: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# 活动任务相关模式
class ActivityTaskResponse(BaseModel):
    task_token: str
    run_id: str
    activity_type: str
    status: str
    input: Optional[str] = None
    result: Optional[str] = None
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CompleteRequest(BaseModel):
    result_data: str

class FailRequest(BaseModel):
    reason: str
    details: Optional[str] = None

class HeartbeatRequest(BaseModel):
    details: Optional[str] = None

# 工作流事件相关模式
class WorkflowEventResponse(BaseModel):
    event_id: int
    run_id: str
    event_type: str
    event_time: datetime
    event_data: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# 定时器相关模式
class TimerResponse(BaseModel):
    timer_id: str
    run_id: str
    fire_time: datetime
    status: str
    
    model_config = ConfigDict(from_attributes=True)

class TimerCreate(BaseModel):
    run_id: str
    fire_time: datetime
    callback_data: Optional[str] = None 
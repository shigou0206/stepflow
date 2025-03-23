from pydantic import BaseModel, Field
from typing import (
    Optional, Dict, Any, List, Union, Literal, Tuple, TypedDict, NamedTuple
)
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path

# -----------------------------------------------------------
# 枚举类型
# -----------------------------------------------------------

class OnError(str, Enum):
    CONTINUE_ERROR_OUTPUT = "continueErrorOutput"
    CONTINUE_REGULAR_OUTPUT = "continueRegularOutput"
    STOP_WORKFLOW = "stopWorkflow"

    @classmethod
    def from_string(cls, value: str) -> "OnError":
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Invalid OnError value: {value}")


class BinaryFileType(str, Enum):
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PDF = "pdf"
    HTML = "html"

    @classmethod
    def from_string(cls, value: str) -> Optional["BinaryFileType"]:
        for item in cls:
            if item.value == value.lower():
                return item
        return None


class NodePropertyTypes(str, Enum):
    BOOLEAN = "boolean"
    BUTTON = "button"
    COLLECTION = "collection"
    COLOR = "color"
    DATETIME = "dateTime"
    FIXED_COLLECTION = "fixedCollection"
    HIDDEN = "hidden"
    JSON = "json"
    NOTICE = "notice"
    MULTI_OPTIONS = "multiOptions"
    NUMBER = "number"
    OPTIONS = "options"
    STRING = "string"
    CREDENTIALS_SELECT = "credentialsSelect"
    RESOURCE_LOCATOR = "resourceLocator"
    CURL_IMPORT = "curlImport"
    RESOURCE_MAPPER = "resourceMapper"
    FILTER = "filter"
    ASSIGNMENT_COLLECTION = "assignmentCollection"
    CREDENTIALS = "credentials"
    WORKFLOW_SELECTOR = "workflowSelector"

    @classmethod
    def from_string(cls, value: str) -> "NodePropertyTypes":
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid NodePropertyType: {value}")


class ConnectionType(str, Enum):
    MAIN = "main"


class CategoryType(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"

    @classmethod
    def from_string(cls, value: str) -> "CategoryType":
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Invalid CategoryType value: {value}")


CallerPolicy = Literal["any", "none", "workflowsFromAList", "workflowsFromSameOwner"]
SaveDataExecution = Literal["DEFAULT", "all", "none"]
DefaultOrBool = Union[Literal["DEFAULT"], bool]
ExecutionOrder = Literal["v0", "v1"]
TimezoneType = Union[Literal["DEFAULT"], str]

# -----------------------------------------------------------
# 基本数据模型
# -----------------------------------------------------------

class BinaryData(BaseModel):
    data: str
    mime_type: str
    file_type: Optional[BinaryFileType] = None
    file_name: Optional[str] = None
    directory: Optional[str] = None
    file_extension: Optional[str] = None
    file_size: int = 0
    id: Optional[str] = None

    def get_full_path(self) -> Optional[Path]:
        if self.directory and self.file_name:
            return Path(self.directory) / self.file_name
        return None

    def is_valid_file(self) -> bool:
        return bool(self.data and self.mime_type and self.file_name)

    def to_dict(self) -> dict:
        # Pydantic 模型也提供 .dict() 方法，但这里可以自定义格式
        return {
            "data": self.data,
            "mime_type": self.mime_type,
            "file_type": self.file_type.value if self.file_type else None,
            "file_name": self.file_name,
            "directory": self.directory,
            "file_extension": self.file_extension,
            "file_size": self.file_size,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BinaryData":
        return cls(
            data=data["data"],
            mime_type=data["mime_type"],
            file_type=BinaryFileType.from_string(data.get("file_type", "")),
            file_name=data.get("file_name"),
            directory=data.get("directory"),
            file_extension=data.get("file_extension"),
            file_size=data.get("file_size", 0),
            id=data.get("id"),
        )

# BinaryKeyData 定义
BinaryKeyData = Dict[str, BinaryData]


class NodeCredentialsDetail(BaseModel):
    name: str
    id: Optional[str] = None


# NodeCredentials 定义：键为字符串，值为 NodeCredentialsDetail
NodeCredentials = Dict[str, NodeCredentialsDetail]


class WorkflowNode(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type_version: Optional[int] = None
    type: Optional[str] = None
    position: Tuple[float, float] = (0.0, 0.0)
    disabled: Optional[bool] = None
    notes: Optional[str] = None
    notes_in_flow: Optional[bool] = None
    retry_on_fail: Optional[bool] = None
    max_tries: Optional[int] = None
    wait_between_tries: Optional[int] = None
    always_output_data: Optional[bool] = None
    execute_once: Optional[bool] = None
    on_error: Optional[OnError] = None
    continue_on_fail: Optional[bool] = None
    parameters: Dict[str, Union[str, int, bool, list, dict]] = Field(default_factory=dict)
    credentials: Optional[NodeCredentials] = None
    webhook_id: Optional[str] = None
    extends_credential: Optional[str] = None


# WorkflowNodes 类型：键为节点名称，值为 WorkflowNode 对象
WorkflowNodes = Dict[str, WorkflowNode]


class NodeSourceData(BaseModel):
    """存储任务数据连接的来源信息"""
    previous_node: str
    previous_node_output: Optional[int] = 0
    previous_node_run: Optional[int] = 0


class PairedItem(BaseModel):
    item: int
    input: Optional[int] = None
    source_overwrite: Optional[NodeSourceData] = None


class RelatedExecution(BaseModel):
    """存储父/子执行的信息"""
    execution_id: str
    workflow_id: str


class TaskSubRunMetadata(BaseModel):
    """存储任务子运行的元数据"""
    node: str
    run_index: int


class NodeExecutionMetadata(BaseModel):
    """任务的元数据"""
    sub_run: Optional[List[TaskSubRunMetadata]] = Field(default_factory=list)
    parent_execution: Optional[RelatedExecution] = None
    sub_execution: Optional[RelatedExecution] = None
    sub_executions_count: Optional[int] = None


class NodeExecutionResult(BaseModel):
    json_data: Any = Field(default_factory=dict)
    binary: Optional[BinaryKeyData] = None
    error: Optional[str] = None
    paired_item: Optional[Union[PairedItem, List[PairedItem], int]] = None
    metadata: Optional[Dict[str, RelatedExecution]] = None
    class Config:
        extra = "allow"


# NodeInputDataMap 定义
NodeInputDataMap = Dict[str, List[Optional[NodeExecutionResult]]]

class NodeExecuteResponse(BaseModel):
    data: Optional[List[List[NodeExecutionResult]]] = None
    hints: Optional[List[str]] = None
    

class NodeTaskResult(BaseModel):
    """存储节点执行后的数据"""
    start_time: float
    execution_time: float
    execution_status: Optional[str] = None  # 你可以使用 WorkflowExecutionStatus.value 替换
    data: Optional[NodeInputDataMap] = None
    input_override: Optional[NodeInputDataMap] = None
    error: Optional[str] = None
    hints: Optional[List[str]] = None  # 这里可以扩展为 NodeExecutionHint 模型
    source: List[Optional[NodeSourceData]] = Field(default_factory=list)
    metadata: Optional[NodeExecutionMetadata] = None


# WorkflowRunData 定义：键为字符串，值为 NodeTaskResult 列表
WorkflowRunData = Dict[str, List[NodeTaskResult]]


class StartNodeData(BaseModel):
    name: str
    source_data: Optional[NodeSourceData] = None


# ExecuteContextData 定义：简单的字典
ExecuteContextData = Dict[str, Dict[str, Any]]


class NodeExecuteContext(BaseModel):
    """存储执行数据，包括任务数据连接、元数据、当前节点信息"""
    data: NodeInputDataMap
    node: WorkflowNode
    source: Optional[Dict[str, List[Optional[NodeSourceData]]]] = None
    metadata: Optional[NodeExecutionMetadata] = None


# 定义 WaitingForExecutionSource、NodesWaitingForInput 和 WorkflowPinnedData
WaitingForExecutionSource = Dict[str, Dict[int, Dict[str, List[Optional[NodeSourceData]]]]]
NodesWaitingForInput = Dict[str, Dict[int, NodeInputDataMap]]
WorkflowPinnedData = Dict[str, List[NodeExecutionResult]]


class StartData(BaseModel):
    start_node_data: Optional[StartNodeData] = None
    run_node_filter: Optional[List[str]] = None
    destination_node_name: Optional[str] = None


class ResultData(BaseModel):
    error: Optional[Any] = None
    runData: Optional[WorkflowRunData] = None
    workflowPinnedData: Optional[WorkflowPinnedData] = None
    lastNodeExecuted: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionData(BaseModel):
    contextData: ExecuteContextData = Field(default_factory=dict)
    nodeExecutionStack: List[NodeExecuteContext] = Field(default_factory=list)
    metadata: Dict[str, NodeExecutionMetadata] = Field(default_factory=dict)
    waitingExecution: Optional[NodesWaitingForInput] = None
    waitingExecutionSource: Optional[WaitingForExecutionSource] = None


class WorkflowExecutionState(BaseModel):
    start_data: Optional[StartNodeData] = None
    result_data: ResultData = Field(default_factory=ResultData)
    execution_data: ExecutionData = Field(default_factory=ExecutionData)
    parent_execution: Optional[RelatedExecution] = None
    wait_till: Optional[datetime] = None
    push_ref: Optional[str] = None
    is_test_webhook: Optional[bool] = False
    manual_data: Optional[Dict[str, Any]] = None


# -----------------------------------------------------------
# 以下为其他数据结构
# -----------------------------------------------------------

class ConnectedNode(BaseModel):
    name: str
    indicies: List[int]
    depth: int


# 这里 DisplayCondition 采用简单模型，实际可根据需求扩展
class DisplayCondition(BaseModel):
    eq: Optional[Union[str, int]] = None
    not_eq: Optional[Union[str, int]] = None
    gte: Optional[Union[str, int]] = None
    lte: Optional[Union[str, int]] = None
    gt: Optional[Union[str, int]] = None
    lt: Optional[Union[str, int]] = None
    between: Optional[Dict[str, Union[str, int]]] = None
    startsWith: Optional[str] = None
    endsWith: Optional[str] = None
    includes: Optional[str] = None
    regex: Optional[str] = None
    exists: Optional[bool] = None


# DisplayOptions 模型
class DisplayOptions(BaseModel):
    hide: Optional[Dict[str, List[DisplayCondition]]] = None
    show: Optional[Dict[str, List[DisplayCondition]]] = None
    hideOnCloud: Optional[bool] = None


NodePropertyTypeOptions = Dict[str, Any]


class NodePropertyOptions(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None


class NodeProperties(BaseModel):
    display_name: str
    name: str
    type: NodePropertyTypes
    default: Optional[Any] = None
    type_options: Optional[NodePropertyTypeOptions] = None
    description: Optional[str] = None
    hint: Optional[str] = None
    disabled_options: Optional[DisplayOptions] = None
    display_options: Optional[DisplayOptions] = None
    options: Optional[List[Union[NodePropertyOptions, "NodeProperties"]]] = None
    placeholder: Optional[str] = None
    is_node_setting: Optional[bool] = False
    no_data_expression: Optional[bool] = False
    required: Optional[bool] = False
    credential_types: Optional[List[str]] = None
    modes: Optional[List[str]] = None
    requires_data_path: Optional[str] = None
    do_not_inherit: Optional[bool] = False
    validate_type: Optional[str] = None
    ignore_validation_during_execution: Optional[bool] = False

class NodeConnection(BaseModel):
    node: str
    connection_type: ConnectionType
    index: int

    class Config:
        use_enum_values = True


NodeInputConnections = List[Optional[List[NodeConnection]]]
NodeConnections = Dict[str, NodeInputConnections]
Connections = Dict[str, NodeConnections]

class WorkflowSettings(BaseModel):
    timezone: Optional[TimezoneType] = None
    error_workflow: Optional[str] = None
    caller_ids: Optional[str] = None
    caller_policy: Optional[CallerPolicy] = None
    save_data_error_execution: Optional[SaveDataExecution] = None
    save_data_success_execution: Optional[SaveDataExecution] = None
    save_manual_executions: Optional[DefaultOrBool] = None
    save_execution_progress: Optional[DefaultOrBool] = None
    execution_timeout: Optional[int] = None
    execution_order: Optional[ExecutionOrder] = None


class NodeOutputConfiguration(BaseModel):
    category: Optional[CategoryType] = None
    display_name: Optional[str] = None
    max_connections: Optional[int] = None
    required: Optional[bool] = None
    type: Optional[ConnectionType] = None


class NodeTypeDescription(BaseModel):
    name: str
    display_name: Optional[str] = None
    icon: Optional[str] = None
    version: Optional[int] = 1
    description: Optional[str] = None
    default_name: Optional[str] = None
    subtitle: Optional[str] = None
    properties: List[NodeProperties] = Field(default_factory=list)
    inputs: Optional[List[Union[str, NodeOutputConfiguration]]] = Field(default_factory=list)
    outputs: Optional[List[Union[str, NodeOutputConfiguration]]] = Field(default_factory=list)
    credentials: Optional[List[str]] = Field(default_factory=list)
    max_nodes: Optional[int] = None
    group: Optional[List[str]] = None
    codex: Optional[Dict[str, Any]] = None
    is_trigger: Optional[bool] = False
    webhook_setup: Optional[Dict[str, Any]] = None


# -----------------------------------------------------------
# 抽象类 NodeType
# -----------------------------------------------------------
class NodeType(ABC):
    def __init__(self, description: NodeTypeDescription):
        self.description = description

    @abstractmethod
    def execute(self, data: Any) -> Any:
        pass


# 如果有更多的数据结构，亦可采用类似方式转换为 Pydantic 模型。
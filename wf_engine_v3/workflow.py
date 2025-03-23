from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Any, Dict, Callable, List, Union
import logging
from datetime import datetime

from .model import WorkflowNode, WorkflowNodes, NodeOutputConfiguration
from .model import Connections, ConnectionType, NodeConnection
from .model import WorkflowSettings, WorkflowPinnedData
from .nodes import node_types_map
from .nodes import NodeType
from .utils import (
    get_node_parameters, 
    get_connections_by_destination, 
    GlobalState, 
    rename_node_in_parameter_value, 
    NODES_WITH_RENAMABLE_CONTENT
)

# -----------------------------
# Pydantic 数据模型定义
# -----------------------------

class WorkflowBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    name: str
    active: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    nodes: List[WorkflowNode] = Field(default_factory=list)
    node_types: Optional[Dict[str, NodeType]] = None
    connections: Connections = Field(default_factory=dict)
    settings: Optional[WorkflowSettings] = None
    static_data: Optional[Dict] = None
    pin_data: Optional[WorkflowPinnedData] = None
    version_id: Optional[str] = None

class ExecuteWorkflowInfo(BaseModel):
    code: Optional[WorkflowBase] = None
    id: Optional[str] = None

class WorkflowParameters(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: Optional[str] = None
    name: Optional[str] = None
    nodes: List[WorkflowNode] = Field(default_factory=list)
    connections: Optional[Connections] = Field(default_factory=dict)
    active: bool = False
    node_types: Optional[Dict[str, NodeType]] = None
    static_data: Optional[Any] = None
    settings: Optional[WorkflowSettings] = None
    pin_data: Optional[WorkflowPinnedData] = None

    @field_validator("connections", mode="before")
    @classmethod
    def convert_connections(cls, value: Any) -> Any:
        new_value = {}
        for node, node_conns in value.items():
            new_node_conns = {}
            for key, connection_list in node_conns.items():
                new_connection_list = []
                for group in connection_list:
                    new_group = []
                    for conn in group:
                        if isinstance(conn, dict):
                            new_group.append(NodeConnection(**conn))
                        else:
                            new_group.append(conn)
                    new_connection_list.append(new_group)
                new_node_conns[key] = new_connection_list
            new_value[node] = new_node_conns
        return new_value

# -----------------------------
# Workflow 类（业务逻辑类）
# -----------------------------
class Workflow:
    def __init__(self, parameters: WorkflowParameters):
        self.id: str = parameters.id or ""
        self.name: Optional[str] = parameters.name
        self.node_types: Optional[Dict[str, NodeType]] = parameters.node_types
        self.nodes: WorkflowNodes = {}
        for node in parameters.nodes:
            self.nodes[node.name] = node
            # 如果有 node_types 信息，可在此处调用 get_node_parameters 进行参数处理
            # node_type = self.node_types.get_by_name_and_version(node.type, node.type_version) if self.node_types else None
            # if node_type:
            #     node.parameters = get_node_parameters(node_type.description.properties, node.parameters, node)

        # connections 这里通过工具函数自动转换
        self.connections_by_destination_node = get_connections_by_destination(parameters.connections)
        self.active = parameters.active
        self.static_data = parameters.static_data or {}
        self.settings = parameters.settings
        self.pin_data = parameters.pin_data or {}
        self.timezone = self.settings.timezone if self.settings else GlobalState.get_global_state().get("defaultTimezone")
        # 用于测试的静态数据，可以后续设置
        self.test_static_data: Optional[Dict[str, Any]] = None
        # 如果有 connections_by_source_node 则初始化
        self.connections_by_source_node: Dict[str, Any] = {}

    def get_static_data(self, context_type: str, node: Optional[WorkflowNode] = None) -> Dict[str, Any]:
        if context_type == "global":
            key = "global"
        elif context_type == "node":
            if node is None:
                raise ValueError('Context type "node" requires a node parameter.')
            key = f"node:{node.name}"
        else:
            raise ValueError(f"Unknown context type: {context_type}. Only 'global' and 'node' are supported.")

        # 如果 test_static_data 存在且包含 key，则返回 test_static_data[key]
        if self.test_static_data and key in self.test_static_data:
            return self.test_static_data[key]

        # 确保静态数据结构存在
        if key not in self.static_data:
            self.static_data[key] = {}

        return self.static_data[key]
    
    def set_test_static_data(self, test_static_data: Dict[str, Any]) -> None:
        self.test_static_data = test_static_data

    def query_nodes(self, check_function: Callable[[Any], bool]) -> List[Any]:
        return_nodes = []
        for node_name, node in self.nodes.items():
            if getattr(node, "disabled", False):
                continue

            node_type = self.node_types.get_by_name_and_version(node.type, getattr(node, "type_version", None))
            if node_type is not None and check_function(node_type):
                return_nodes.append(node)
        return return_nodes

    def get_trigger_nodes(self) -> List[Any]:
        return self.query_nodes(lambda node_type: bool(getattr(node_type, "trigger", False)))

    def get_poll_nodes(self) -> List[Any]:
        return self.query_nodes(lambda node_type: bool(getattr(node_type, "poll", False)))
    
    def get_node(self, node_name: str) -> Optional[Any]:
        return self.nodes.get(node_name, None)
    
    def get_nodes(self, node_names: List[str]) -> List[Any]:
        nodes = []
        for name in node_names:
            node = self.get_node(name)
            if not node:
                logging.warning(f"Could not find a node with the name '{name}' in the workflow.")
                continue
            nodes.append(node)
        return nodes
    
    def get_pin_data_of_node(self, node_name: str) -> Optional[List[Any]]:
        return self.pin_data.get(node_name)
    
    def rename_node(self, current_name: str, new_name: str):
        if current_name in self.nodes:
            self.nodes[new_name] = self.nodes.pop(current_name)
            self.nodes[new_name].name = new_name

        for node in self.nodes.values():
            node.parameters = rename_node_in_parameter_value(node.parameters, current_name, new_name)

            if node.type in NODES_WITH_RENAMABLE_CONTENT:
                if "jsCode" in node.parameters:
                    node.parameters["jsCode"] = rename_node_in_parameter_value(
                        node.parameters["jsCode"], current_name, new_name, has_renamable_content=True
                    )

        if current_name in self.connections_by_source_node:
            self.connections_by_source_node[new_name] = self.connections_by_source_node.pop(current_name)

        for source_node, connections in self.connections_by_source_node.items():
            for connection_type, connection_list in connections.items():
                for source_index, connection_group in enumerate(connection_list):
                    for i, connection in enumerate(connection_group):
                        if connection.node == current_name:
                            connection_group[i] = NodeConnection(
                                node=new_name,
                                connection_type=connection.connection_type,
                                index=connection.index
                            )

        self.connections_by_destination_node = get_connections_by_destination(self.connections_by_source_node)

    def get_highest_node(
        self, node_name: str, node_connection_index: Optional[int] = None, checked_nodes: Optional[List[str]] = None
    ) -> List[str]:
        if checked_nodes is None:
            checked_nodes = []

        current_highest = []
        if not self.nodes[node_name].disabled:
            current_highest.append(node_name)

        if node_name not in self.connections_by_destination_node:
            return current_highest

        if ConnectionType.MAIN not in self.connections_by_destination_node[node_name]:
            return current_highest

        if node_name in checked_nodes:
            return current_highest
        checked_nodes.append(node_name)

        return_nodes = []
        for connection_index, connections in enumerate(self.connections_by_destination_node[node_name][ConnectionType.MAIN]):
            if node_connection_index is not None and node_connection_index != connection_index:
                continue

            for connection in connections:
                if connection.node in checked_nodes:
                    continue

                if connection.node not in self.nodes:
                    continue

                add_nodes = self.get_highest_node(connection.node, None, checked_nodes)
                if not add_nodes:
                    if not self.nodes[connection.node].disabled:
                        add_nodes = [connection.node]

                for name in add_nodes:
                    if name not in return_nodes:
                        return_nodes.append(name)
        return return_nodes
    
    def get_node_outputs(self, node, node_type_data) -> List[Union[str, NodeOutputConfiguration]]:
        if isinstance(node_type_data.outputs, list):
            outputs = node_type_data.outputs
        else:
            try:
                outputs = self.expression.get_simple_parameter_value(
                    node,
                    node_type_data.outputs,
                    mode="internal",
                    additional_keys={},
                ) or []
            except Exception:
                print(f"Could not calculate outputs dynamically for node: {node.name}")
                outputs = []

        if node.on_error == "continueErrorOutput":
            outputs = outputs.copy()
            if len(outputs) == 1:
                if isinstance(outputs[0], str):
                    outputs[0] = NodeOutputConfiguration(type=outputs[0], display_name="Success")
                else:
                    outputs[0].display_name = "Success"
            outputs.append(NodeOutputConfiguration(type=ConnectionType.MAIN, category="error", display_name="Error"))
        return outputs
    
    def get_parent_main_input_node(self, node: WorkflowNode) -> Optional[WorkflowNode]:
        if node is None:
            return None

        node_type = self.node_types.get_by_name_and_version(node.node_type, node.type_version)
        outputs = self.get_node_outputs(node, node_type.description)
        non_main_nodes_connected = []
        for output in outputs:
            output_type = output.type if isinstance(output, NodeOutputConfiguration) else output
            if output_type != ConnectionType.MAIN:
                parent_nodes = self.get_child_nodes(node.name, output_type)
                if parent_nodes:
                    non_main_nodes_connected.extend(parent_nodes)
        if non_main_nodes_connected:
            return_node = self.get_node(non_main_nodes_connected[0])
            if return_node is None:
                raise RuntimeError(f'Node "{non_main_nodes_connected[0]}" not found')
            return self.get_parent_main_input_node(return_node)
        return node
    
    def get_node_connection_indexes(
        self,
        node_name: str,
        parent_node_name: str,
        connection_type: ConnectionType = ConnectionType.MAIN,
        depth: int = -1,
        checked_nodes: Optional[List[str]] = None,
    ) -> Optional[dict]:
        node = self.get_node(parent_node_name)
        if node is None:
            return None

        depth = depth if depth == -1 else depth - 1
        if depth == 0:
            return None  # 达到最大深度

        if node_name not in self.connections_by_destination_node:
            return None
        if connection_type not in self.connections_by_destination_node[node_name]:
            return None

        checked_nodes = checked_nodes or []
        if node_name in checked_nodes:
            return None  # 防止无限循环

        checked_nodes.append(node_name)

        for connections_by_index in self.connections_by_destination_node[node_name][connection_type]:
            if not connections_by_index:
                continue
            for destination_index, connection in enumerate(connections_by_index):
                if parent_node_name == connection["node"]:
                    return {"sourceIndex": connection["index"], "destinationIndex": destination_index}
                if connection["node"] in checked_nodes:
                    continue
                output_index = self.get_node_connection_indexes(
                    connection["node"], parent_node_name, connection_type, depth, checked_nodes
                )
                if output_index is not None:
                    return output_index
        return None
    
    def _get_start_node(self, node_names: List[str]) -> Optional[WorkflowNode]:
        for node_name in node_names:
            node = self.nodes.get(node_name)
            if not node:
                continue
            if len(node_names) == 1 and not node.disabled:
                return node
            if node_name == 'Start':
                return node

            # node_type = self.node_types.get_by_name_and_version(node.type, node.type_version)
            # if node_type.description.name == "MANUAL_CHAT_TRIGGER_LANGCHAIN_NODE_TYPE":
            #     continue
            # if (node_type and (hasattr(node_type, "trigger") or hasattr(node_type, "poll"))) and not node.disabled:
            #     return node
        return None
    
    def get_start_node(self, destination_node: Optional[str] = None) -> Optional[WorkflowNode]:
        if destination_node:
            node_names = self.get_highest_node(destination_node)
            if not node_names:
                node_names.append(destination_node)
            start_node = self._get_start_node(node_names)
            if start_node:
                return start_node
            return self.nodes.get(node_names[0])
        return self._get_start_node(list(self.nodes.keys()))
from typing import Optional, List, Dict, Any, Union
from .model import NodeProperties, ConnectedNode
from .model import NodeConnection, Connections, ConnectionType
from collections import defaultdict, deque
import copy
import re


NODES_WITH_RENAMABLE_CONTENT = {
    "CODE_NODE_TYPE",
    "FUNCTION_NODE_TYPE",
    "FUNCTION_ITEM_NODE_TYPE",
    "AI_TRANSFORM_NODE_TYPE",
}

class GlobalState:
    """Manages global state settings such as timezone."""
    
    _state: Dict[str, str] = {"defaultTimezone": "America/New_York"}

    @classmethod
    def set_global_state(cls, state: Dict[str, str]) -> None:
        """
        Updates the global state.

        :param state: A dictionary representing the new global state.
        """
        cls._state = state

    @classmethod
    def get_global_state(cls) -> Dict[str, str]:
        """
        Returns a deep copy of the global state to prevent modification.

        :return: A dictionary containing the global state.
        """
        return copy.deepcopy(cls._state)

def get_parameter_dependencies(node_properties_array: List[NodeProperties]) -> Dict[str, List[str]]:
    dependencies: Dict[str, List[str]] = {}

    for node_properties in node_properties_array:
        name = node_properties.name
        display_options = node_properties.display_options

        if not isinstance(name, str) or not name.strip():
            continue

        if name not in dependencies:
            dependencies[name] = []

        if not isinstance(display_options, dict):
            continue

        for display_rule in display_options.values():
            if not isinstance(display_rule, dict):
                continue

            for parameter_name in display_rule.keys():
                if isinstance(parameter_name, str) and not parameter_name.startswith("@"):
                    if parameter_name not in dependencies[name]:
                        dependencies[name].append(parameter_name)

    return dependencies

def get_parameter_resolve_order(
    node_properties_array: List[NodeProperties],
    parameter_dependencies: Dict[str, List[str]],
) -> List[int]:
    execution_order: List[int] = []
    index_to_resolve = list(range(len(node_properties_array)))
    resolved_parameters: List[str] = []
    dependency_check = {prop.name: set(parameter_dependencies.get(prop.name, [])) for prop in node_properties_array}

    last_index_length = len(index_to_resolve)
    last_index_reduction = -1
    iterations = 0
    max_iterations = len(node_properties_array) * 2  # Avoid infinite loops

    while index_to_resolve:
        iterations += 1

        if iterations > max_iterations:
            raise RuntimeError(
                "Circular dependency detected! Could not resolve parameter dependencies."
            )

        index = index_to_resolve.pop(0)
        property_name = node_properties_array[index].name

        if not parameter_dependencies.get(property_name):
            execution_order.append(index)
            resolved_parameters.append(property_name)
            continue

        dependencies = parameter_dependencies[property_name]
        unresolved_dependencies = [
            dep for dep in dependencies if dep not in resolved_parameters and not dep.startswith("/")
        ]

        if unresolved_dependencies:
            index_to_resolve.append(index)
            continue

        execution_order.append(index)
        resolved_parameters.append(property_name)

        if len(index_to_resolve) < last_index_length:
            last_index_reduction = iterations

        last_index_length = len(index_to_resolve)

    return execution_order


def get_node_parameters(
    node_properties_array: List[NodeProperties],
    node_values: Optional[Dict[str, Any]],
    return_defaults: bool,
    return_none_displayed: bool,
    node: Optional[Dict[str, Any]],
    only_simple_types: bool = False,
    data_is_resolved: bool = False,
    node_values_root: Optional[Dict[str, Any]] = None,
    parent_type: Optional[str] = None,
    parameter_dependencies: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """ Fully aligned version of getNodeParameters from TypeScript to Python """

    if parameter_dependencies is None:
        parameter_dependencies = get_parameter_dependencies(node_properties_array)

    duplicate_parameter_names = set()
    parameter_names = set()

    for node_properties in node_properties_array:
        name = node_properties.name
        if name in parameter_names:
            duplicate_parameter_names.add(name)
        else:
            parameter_names.add(name)

    node_parameters: Dict[str, Any] = {}
    node_parameters_full: Dict[str, Any] = {}

    # Preprocess node values to check displayed parameters
    node_values_display_check = node_parameters_full
    if not data_is_resolved and not return_none_displayed:
        node_values_display_check = get_node_parameters(
            node_properties_array,
            node_values,
            return_defaults=True,
            return_none_displayed=True,
            node=node,
            only_simple_types=True,
            data_is_resolved=True,
            node_values_root=node_values_root,
            parent_type=parent_type,
            parameter_dependencies=parameter_dependencies,
        )

    node_values_root = node_values_root or node_values_display_check

    parameter_iteration_order = get_parameter_resolve_order(node_properties_array, parameter_dependencies)

    for parameter_index in parameter_iteration_order:
        node_properties = node_properties_array[parameter_index]
        name = node_properties.name

        if not node_values or (name not in node_values and (not return_defaults or parent_type == "collection")):
            continue

        if name in duplicate_parameter_names:
            continue

        # Process simple types
        if node_properties.type not in {"collection", "fixedCollection"}:
            if return_defaults:
                node_parameters[name] = node_values.get(name, node_properties.default)
            elif name in node_values and node_values[name] != node_properties.default:
                node_parameters[name] = node_values[name]

        if only_simple_types:
            continue  # Skip deeper processing

        # Handle complex parameter types: collections
        if node_properties.type == "collection":
            if node_properties.type_options and node_properties.type_options.get("multipleValues"):
                # If multiple values are allowed, return array directly
                node_parameters[name] = node_values.get(name, []) if return_defaults else node_values.get(name)
            else:
                # Otherwise, recursively resolve parameters inside the collection
                temp_node_parameters = get_node_parameters(
                    node_properties.options or [],
                    node_values.get(name, {}),
                    return_defaults,
                    return_none_displayed,
                    node,
                    False,
                    False,
                    node_values_root,
                    node_properties.type,
                )
                if temp_node_parameters:
                    node_parameters[name] = temp_node_parameters

        elif node_properties.type == "fixedCollection":
            collection_values: Dict[str, Any] = {}
            property_values = node_values.get(name, {} if return_defaults else None)

            if return_defaults and not property_values:
                property_values = node_properties.default

            for item_name, value in (property_values or {}).items():
                if isinstance(value, list):
                    collection_values[item_name] = [
                        get_node_parameters(
                            node_properties.options or [], v, return_defaults, return_none_displayed, node, False, False, node_values_root, node_properties.type
                        ) for v in value
                    ]
                else:
                    collection_values[item_name] = get_node_parameters(
                        node_properties.options or [], value, return_defaults, return_none_displayed, node, False, False, node_values_root, node_properties.type
                    )

            node_parameters[name] = collection_values

    return node_parameters

def get_connections_by_destination(connections: Connections) -> Connections:
    return_connections: Connections = defaultdict(lambda: defaultdict(list))
    
    for source_node, node_connections in connections.items():
        for connection_type, input_connections in node_connections.items():
            for input_index, connection_list in enumerate(input_connections or []):
                if not connection_list:
                    continue

                for connection_info in connection_list:
                    dest_node = connection_info.node
                    dest_type = connection_info.connection_type
                    dest_index = connection_info.index

                    while len(return_connections[dest_node][dest_type]) <= dest_index:
                        return_connections[dest_node][dest_type].append([])

                    return_connections[dest_node][dest_type][dest_index].append(
                        NodeConnection(node=source_node, connection_type=connection_type, index=input_index)
                    )

    return return_connections


def backslash_escape(value: str) -> str:
    """对字符串进行反斜杠转义以便于正则匹配"""
    return re.escape(value)


def dollar_escape(value: str) -> str:
    """用于替换 `new_name`，确保符合 `$node[...]` 格式"""
    return value.replace('"', '\\"').replace("'", "\\'")


def has_dot_notation_banned_char(value: str) -> bool:
    """检查新名称是否包含点号，可能需要用 `["..."]` 代替点符号"""
    return "." in value


def rename_node_in_parameter_value(
    parameter_value: Union[str, List[Any], Dict[str, Any]],
    current_name: str,
    new_name: str,
    has_renamable_content: bool = False
) -> Union[str, List[Any], Dict[str, Any]]:

    if not isinstance(parameter_value, (str, list, dict)):
        return parameter_value

    if isinstance(parameter_value, str):
        # 只处理以 `=` 开头或允许重命名的字符串
        if not (parameter_value.startswith("=") or has_renamable_content):
            return parameter_value

        # 先检查是否包含当前名称，避免不必要的正则替换
        if current_name not in parameter_value:
            return parameter_value

        escaped_old_name = backslash_escape(current_name)
        escaped_new_name = dollar_escape(new_name)

        def replace_pattern(expression: str, old_pattern: str) -> str:
            return re.sub(old_pattern, rf"\1{escaped_new_name}\2", expression)

        # 处理不同格式的节点引用
        if "$(" in parameter_value:
            old_pattern = rf"(\$\(['\"]){escaped_old_name}(['\"]\))"
            parameter_value = replace_pattern(parameter_value, old_pattern)

        if "$node[" in parameter_value:
            old_pattern = rf"(\$node\[['\"]){escaped_old_name}(['\"]\])"
            parameter_value = replace_pattern(parameter_value, old_pattern)

        if "$node." in parameter_value:
            old_pattern = rf"(\$node\.){escaped_old_name}(\.?)"
            parameter_value = replace_pattern(parameter_value, old_pattern)

            if has_dot_notation_banned_char(new_name):
                parameter_value = re.sub(
                    rf"\.{backslash_escape(new_name)}(\s|\.)",
                    rf'["{escaped_new_name}"]\1',
                    parameter_value
                )

        if "$items(" in parameter_value:
            old_pattern = rf"(\$items\(['\"]){escaped_old_name}(['\"],|['\"]\))"
            parameter_value = replace_pattern(parameter_value, old_pattern)

        return parameter_value

    if isinstance(parameter_value, list):
        return [rename_node_in_parameter_value(value, current_name, new_name) for value in parameter_value]

    if isinstance(parameter_value, dict):
        return {
            key: rename_node_in_parameter_value(value, current_name, new_name, has_renamable_content)
            for key, value in parameter_value.items()
        }

    return parameter_value

def get_connected_nodes(
    connections: Connections,
    node_name: str,
    connection_type: Union[ConnectionType, str] = ConnectionType.MAIN,
    depth: int = -1,
    checked_nodes: Optional[List[str]] = None,
) -> List[str]:
    """
    获取与指定节点连接的所有节点。
    
    :param connections: 连接字典
    :param node_name: 节点名称
    :param connection_type: 连接类型，默认为 MAIN
    :param depth: 搜索深度，-1 表示不限制
    :param checked_nodes: 已检查的节点列表，用于避免循环
    :return: 连接的节点名称列表
    """
    if checked_nodes is None:
        checked_nodes = []

    if node_name in checked_nodes:
        return []

    checked_nodes.append(node_name)

    if node_name not in connections:
        return []

    new_depth = depth
    if depth != -1:
        new_depth = depth - 1
        if new_depth == 0:
            return []

    types = []
    if isinstance(connection_type, str):
        types = [connection_type]
    else:
        types = [connection_type]

    return_nodes = []

    for conn_type in types:
        if conn_type not in connections[node_name]:
            continue

        for connections_by_index in connections[node_name][conn_type]:
            for connection in connections_by_index:
                if connection.node in checked_nodes:
                    continue

                return_nodes.insert(0, connection.node)

                add_nodes = get_connected_nodes(
                    connections, connection.node, connection_type, new_depth, checked_nodes
                )

                for parent_node in reversed(add_nodes):
                    if parent_node in return_nodes:
                        return_nodes.remove(parent_node)
                    return_nodes.insert(0, parent_node)

    return return_nodes

def get_child_nodes(
    connections_by_source: Connections,
    node_name: str,
    connection_type: Union[ConnectionType, str] = ConnectionType.MAIN,
    depth: int = -1,
) -> List[str]:
    return get_connected_nodes(connections_by_source, node_name, connection_type, depth)

def get_parent_nodes(
    connections_by_destination: Connections,
    node_name: str,
    connection_type: Union[ConnectionType, str] = ConnectionType.MAIN,
    depth: int = -1,
) -> List[str]:
    return get_connected_nodes(connections_by_destination, node_name, connection_type, depth)

def search_nodes_bfs(connections: Connections, source_node: str, max_depth: int = -1) -> List[ConnectedNode]:
    """
    执行广度优先搜索 (BFS)，查找 `source_node` 可达的所有子节点。

    :param connections: 连接字典，记录节点间的关系
    :param source_node: 搜索起点节点名称
    :param max_depth: 最大搜索深度，-1 表示不限制
    :return: 目标节点列表，包含其名称、深度和索引
    """
    return_conns = []  # 结果列表
    type_ = ConnectionType.MAIN
    queue = deque([ConnectedNode(name=source_node, depth=0, indices=[])])
    visited: Dict[str, ConnectedNode] = {}

    depth = 0
    while queue:
        if max_depth != -1 and depth > max_depth:
            break
        depth += 1

        to_add = list(queue)
        queue.clear()

        for curr in to_add:
            if curr.name in visited:
                # 去重处理，合并 indices
                visited[curr.name].indices = list(set(visited[curr.name].indices + curr.indices))
                continue

            visited[curr.name] = curr
            if curr.name != source_node:
                return_conns.append(curr)

            if curr.name not in connections or type_ not in connections[curr.name]:
                continue

            for connections_by_index in connections[curr.name][type_]:
                if connections_by_index:
                    for connection in connections_by_index:
                        queue.append(ConnectedNode(name=connection.node, depth=depth, indices=[connection.index]))

    return return_conns

def get_parent_nodes_by_depth(connections_by_destination: Connections, node_name: str, max_depth: int = -1) -> List[ConnectedNode]:
    return search_nodes_bfs(connections_by_destination, node_name, max_depth)


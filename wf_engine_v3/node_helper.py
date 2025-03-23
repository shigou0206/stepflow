from wf_engine_v3.workflow import Workflow, WorkflowParameters, WorkflowSettings
from wf_engine_v3.model import NodeExecuteContext, NodeExecuteResponse
from wf_engine_v3.nodes import node_types_map
from wf_engine_v3.workflow import WorkflowNode
from typing import Dict, Any, List

def run_node(
        workflow: Workflow, 
        node_execute_context: NodeExecuteContext, 
        additional_context: Dict[str, Any] = None) -> NodeExecuteResponse:
    node = node_execute_context.node
    input_data = node_execute_context.data 

    if node.disabled:
        if 'main' in input_data and len(input_data['main']) > 0:
            data = input_data['main'][0]
            return NodeExecuteResponse(data=data)
        else:
            return NodeExecuteResponse(data=[])
        
    node_type = workflow.node_types[node.type]
    return node_type


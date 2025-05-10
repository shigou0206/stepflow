
from stepflow.dsl.dsl_model import WorkflowDSL, State, MapState, ParallelState, Branch
from typing import List, Set


def collect_references(states: dict, scope: Set[str]) -> Set[str]:
    """Collect all state names referenced via Next, Catch, Choice, etc."""
    referenced = set()
    for state in states.values():
        if getattr(state, "Next", None):
            referenced.add(state.Next)
        if getattr(state, "catch", None):
            for c in state.catch:
                referenced.add(c.next)
        if getattr(state, "type", "") == "Choice":
            for choice in getattr(state, "choices", []):
                referenced.add(choice.next)
            if getattr(state, "default", None):
                referenced.add(state.default)
    return referenced


def validate_branch(branch: Branch, parent: str) -> List[str]:
    errors = []
    if branch.start_at not in branch.states:
        errors.append(f"[{parent}] StartAt '{branch.start_at}' not found in branch States")
    scope = set(branch.states.keys())
    refs = collect_references(branch.states, scope)
    for ref in refs:
        if ref not in scope:
            errors.append(f"[{parent}] Referenced state '{ref}' does not exist in branch scope")
    return errors


def validate_semantic(dsl: WorkflowDSL) -> List[str]:
    errors = []
    states = dsl.states
    start = dsl.start_at

    if start not in states:
        errors.append(f'StartAt "{start}" not found in States')

    global_defined = set(states.keys())
    global_referenced = set()

    for name, state in states.items():
        if state.Next:
            global_referenced.add(state.Next)
        if state.Catch:
            for c in state.Catch:
                global_referenced.add(c.Next)
        if getattr(state, "Type", "") == "Choice":
            for choice in getattr(state, "Choices", []):
                global_referenced.add(choice.Next)
            if getattr(state, "Default", None):
                global_referenced.add(state.Default)

        # Validate Map subgraph
        if isinstance(state, MapState):
            errors += validate_branch(state.Iterator, f"Map::{name}")

        # Validate Parallel branches
        if isinstance(state, ParallelState):
            for i, branch in enumerate(state.Branches):
                errors += validate_branch(branch, f"Parallel::{name}::branch{i+1}")

    for ref in global_referenced:
        if ref not in global_defined:
            errors.append(f'Referenced state "{ref}" does not exist in global States')

    unreachable = global_defined - global_referenced - {start}
    if unreachable:
        errors.append(f"Unreachable or unused global states: {', '.join(unreachable)}")

    return errors

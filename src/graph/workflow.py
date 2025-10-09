"""LangGraph workflow definition for Supervisor Agent System"""

from typing import TypedDict, List, Dict, Any, Literal, NotRequired
from langgraph.graph import StateGraph, END
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.agents.supervisor import supervisor_node
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State schema for the agent workflow"""
    objective: str
    # Optional at input time; initialize_node fills defaults
    todo_list: NotRequired[List[Dict[str, Any]]]
    completed_tasks: NotRequired[List[Dict[str, Any]]]
    current_task: NotRequired[Dict[str, Any]]
    iteration_count: NotRequired[int]
    final_result: NotRequired[str]
    max_iterations: NotRequired[int]
    # Visualization helpers (optional)
    route: NotRequired[str]
    next_task_id: NotRequired[int]
    pending_count: NotRequired[int]


def initialize_node(state: AgentState) -> AgentState:
    """Initialize defaults and normalize state for visualization.

    This is a lightweight pass-through that ensures required fields exist
    so downstream nodes have a consistent view. No business logic changes.
    """
    # Ensure required keys exist
    state.setdefault("objective", "")
    state.setdefault("todo_list", [])
    state.setdefault("completed_tasks", [])
    state.setdefault("current_task", {})
    state.setdefault("iteration_count", 0)
    state.setdefault("final_result", "")
    state.setdefault("max_iterations", 20)
    # Optional helpers for Studio visibility
    state.setdefault("route", "plan")
    state.setdefault("next_task_id", None)
    return state


def create_initial_state(objective: str, max_iterations: int = 20) -> AgentState:
    """Create initial state for the workflow"""
    return {
        "objective": objective,
        "todo_list": [],
        "completed_tasks": [],
        "current_task": {},
        "iteration_count": 0,
        "final_result": "",
        "max_iterations": max_iterations
    }


def execute_task_node(state: AgentState) -> AgentState:
    """Perform execution based on routing hints set by supervisor.

    - route == 'plan': planning happens via SupervisorAgent's plan path
    - route == 'execute': execute next task via SupervisorAgent
    - route == 'finalize': synthesis via SupervisorAgent

    This preserves existing behavior by invoking the same SupervisorAgent
    operations, but moves the invocation into this node so Studio visualizes
    work here.
    """
    try:
        from core.agents.supervisor import SupervisorAgent  # type: ignore
        # Reuse the initialized agent from supervisor node if available
        sup_node = supervisor_node  # imported at top
        if hasattr(sup_node, '_supervisor_agent'):
            agent = sup_node._supervisor_agent  # type: ignore
        else:
            # If for some reason it's not initialized yet, just return state
            logger.warning("Supervisor agent not initialized yet; skipping execute_task work")
            return state

        route = state.get("route", "plan")
        next_task_id = state.get("next_task_id")

        result = agent.execute_action(state=state, action=route, task_id=next_task_id)

        # CRITICAL FIX: Apply the result back to state to preserve changes
        if result.get("success", False):
            # Update state with the result from execute_action
            if route == "finalize" and result.get("result"):
                # Set final_result when finalizing
                state["final_result"] = result["result"]
                logger.info("🎯 Final result set in state")
            
            # For all actions, sync with todo_manager to ensure state consistency
            # This is critical because the supervisor agent works through tools
            # that update the global todo_manager, not the state directly
            try:
                from core.tools.supervisor_tools import todo_manager
                state["todo_list"] = todo_manager.get_all_tasks()
                state["completed_tasks"] = [t for t in state["todo_list"] if t.get("status") == "completed"]
                logger.info(f"🔄 Synced state with todo_manager: {len(state['todo_list'])} total tasks, {len(state['completed_tasks'])} completed")
            except Exception as e:
                logger.error(f"Failed to sync with todo_manager: {e}")
        
        # Optional: you could record messages to a safe field like 'log_messages'
        # but avoid 'messages' which is a reserved channel in LangGraph.
        try:
            msg = result.get("result", "")
            if msg:
                logs = state.get("log_messages")
                if isinstance(logs, list):
                    logs.append(str(msg))
                else:
                    state["log_messages"] = [str(msg)]  # type: ignore
        except Exception:
            pass

        return state
    except Exception as e:
        logger.error(f"Error in execute_task_node: {e}")
        return state


def update_state_node(state: AgentState) -> AgentState:
    """Synchronize state after execution for clear Studio visibility.

    Pulls the latest todo list from the todo manager and derives completed/pending
    counts. This centralizes state sync without changing core behavior.
    """
    try:
        from core.tools.supervisor_tools import todo_manager  # type: ignore
        state["todo_list"] = todo_manager.get_all_tasks()
        state["completed_tasks"] = [t for t in state["todo_list"] if t.get("status") == "completed"]
        # Optional: expose a pending count for Studio
        state["pending_count"] = len([t for t in state["todo_list"] if t.get("status") == "pending"])  # type: ignore
    except Exception:
        pass
    return state


def finalize_node(state: AgentState) -> AgentState:
    """Finalize node that ensures final result is properly set.

    The finalize action itself is invoked in execute_task when route=='finalize'.
    This node ensures the final result is properly preserved in the state.
    """
    # Ensure final result is set if not already set
    if not state.get("final_result"):
        # Create a basic final result if none exists
        completed_tasks = state.get("completed_tasks", [])
        todo_list = state.get("todo_list", [])
        
        final_result = f"""## Task Execution Summary

**Completed Tasks**: {len(completed_tasks)}
**Total Tasks**: {len(todo_list)}

### Completed Work:
"""
        for task in completed_tasks:
            final_result += f"- {task.get('task', 'Unknown task')}\n"
            if task.get('result'):
                final_result += f"  Result: {task.get('result')[:200]}...\n"
            if task.get('artifacts'):
                final_result += f"  Files: {task.get('artifacts')}\n"
        
        final_result += f"\n**All tasks completed successfully.**"
        state["final_result"] = final_result
        logger.info("🎯 Final result set in finalize_node")
    
    logger.info(f"🏁 Finalize node completed - Final result: {state.get('final_result', 'None')[:100]}...")
    return state


def should_continue(state: AgentState) -> Literal["supervisor", "end"]:
    """Determine if workflow should continue or end"""

    # 1) End immediately if supervisor has produced a final result
    if state.get("final_result"):
        logger.info("Final result present - ending workflow")
        return "end"

    # 2) If no tasks yet, give the supervisor a chance to plan (first 2 iterations)
    if not state.get("todo_list"):
        if state.get("iteration_count", 0) < 2:
            logger.info("No tasks yet - allowing planning iteration")
            return "supervisor"
        else:
            logger.warning("No tasks created after 2 iterations - ending workflow")
            return "end"

    # 3) End when there are no pending tasks
    pending_tasks = [
        task for task in state.get("todo_list", [])
        if task.get("status") == "pending"
    ]
    if not pending_tasks:
        logger.info("All tasks completed - ending workflow")
        return "end"

    # 4) As a safety net, end on iteration cap
    if state.get("iteration_count", 0) >= state.get("max_iterations", 20):
        logger.warning(f"Max iterations ({state['max_iterations']}) reached")
        return "end"

    # 5) Otherwise continue the loop
    return "supervisor"


def create_workflow() -> StateGraph:
    """Create and compile the LangGraph workflow"""
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("execute_task", execute_task_node)
    workflow.add_node("update_state", update_state_node)
    workflow.add_node("finalize", finalize_node)
    
    # Set entry point
    workflow.set_entry_point("initialize")
    
    # Route through visualization nodes, then decide whether to continue or end
    workflow.add_edge("initialize", "supervisor")
    workflow.add_edge("supervisor", "execute_task")
    workflow.add_edge("execute_task", "update_state")
    workflow.add_conditional_edges(
        "update_state",
        should_continue,
        {
            "supervisor": "supervisor",
            "end": "finalize"
        }
    )
    workflow.add_edge("finalize", END)
    
    return workflow


# Compile the graph for LangGraph Studio
graph = create_workflow().compile()


# Convenience function for direct execution
def run_workflow(objective: str, max_iterations: int = 20) -> AgentState:
    """
    Run the workflow with a given objective
    
    Args:
        objective: The task objective to accomplish
        max_iterations: Maximum number of iterations
        
    Returns:
        Final state after workflow completion
    """
    initial_state = create_initial_state(objective, max_iterations)
    
    logger.info(f"Starting workflow with objective: {objective}")
    
    final_state = graph.invoke(initial_state)
    
    # Persist traces and results at workflow level
    try:
        from src.core.agents.supervisor import persist_traces_and_results
        
        # Collect execution results from final state
        execution_results = []
        for task in final_state.get("completed_tasks", []):
            if task.get('result'):
                execution_results.append({
                    "task_id": task.get('id'),
                    "description": task.get('task'),
                    "result": task.get('result'),
                    "artifacts": task.get('artifacts', []),
                    "status": task.get('status')
                })
        
        # Persist comprehensive traces
        persist_traces_and_results(final_state, execution_results)
        logger.info("💾 Workflow traces and results persisted successfully")
        
    except Exception as e:
        logger.error(f"Failed to persist workflow traces: {e}")
    
    logger.info("Workflow completed")
    
    return final_state


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    test_objective = """
    Create a simple analysis:
    1. Create data.txt with numbers: 5, 10, 15, 20
    2. Calculate their sum
    3. Report the result
    """
    
    result = run_workflow(test_objective)
    
    print("\n" + "="*60)
    print("WORKFLOW RESULT")
    print("="*60)
    print(f"Objective: {result['objective']}")
    print(f"Iterations: {result['iteration_count']}")
    print(f"Tasks completed: {len(result['completed_tasks'])}")
    print(f"Final result: {result.get('final_result', 'No result')}")
    print("="*60)

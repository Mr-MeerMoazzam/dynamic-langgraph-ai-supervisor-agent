"""LangGraph workflow definition for Supervisor Agent System"""

from typing import TypedDict, List, Dict, Any, Literal
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
    todo_list: List[Dict[str, Any]]
    completed_tasks: List[Dict[str, Any]]
    current_task: Dict[str, Any]
    iteration_count: int
    final_result: str
    max_iterations: int


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


def should_continue(state: AgentState) -> Literal["supervisor", "end"]:
    """Determine if workflow should continue or end"""
    
    # Check iteration limit
    if state["iteration_count"] >= state.get("max_iterations", 20):
        logger.warning(f"Max iterations ({state['max_iterations']}) reached")
        return "end"
    
    # Check if all tasks are completed
    pending_tasks = [
        task for task in state.get("todo_list", [])
        if task.get("status") == "pending"
    ]
    
    if not pending_tasks:
        logger.info("All tasks completed - ending workflow")
        return "end"
    
    # Check if there are any tasks at all
    if not state.get("todo_list"):
        # First iteration - allow supervisor to create plan
        if state["iteration_count"] < 2:
            return "supervisor"
        else:
            logger.warning("No tasks created after 2 iterations")
            return "end"
    
    return "supervisor"


def create_workflow() -> StateGraph:
    """Create and compile the LangGraph workflow"""
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "supervisor": "supervisor",
            "end": END
        }
    )
    
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

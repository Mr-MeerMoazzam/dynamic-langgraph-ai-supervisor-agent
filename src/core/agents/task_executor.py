"""
Task Executor implementation for the LangGraph-based Supervisor system.

This module contains the execute_task_node function that handles the execution
of individual tasks by creating and running subagents via the task_tool.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain.schema import AIMessage, HumanMessage

from src.core.state import AgentState, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED
from src.core.tools.supervisor_tools import task_tool

# Configure logging
logger = logging.getLogger(__name__)


def execute_task_node(state: AgentState) -> AgentState:
    """
    Execute the current task using task_tool and update state with results.
    
    This function retrieves the current task from state, executes it using
    the task_tool (which creates and runs a subagent), and updates the state
    with the execution results.
    
    Args:
        state: Current agent state containing the task to execute
        
    Returns:
        Updated agent state with task execution results
    """
    logger.info("=" * 60)
    logger.info("TASK EXECUTOR NODE - Starting task execution")
    logger.info("=" * 60)
    
    try:
        # Get current task from state
        current_task = state.get("current_task")
        if not current_task:
            logger.warning("No current task found in state")
            state["messages"].append(AIMessage(content="No current task to execute"))
            return state
        
        task_id = current_task.get("id")
        task_description = current_task.get("description", "No description")
        assigned_tools = current_task.get("assigned_tools", [])
        
        logger.info(f"Executing Task ID: {task_id}")
        logger.info(f"Task Description: {task_description}")
        logger.info(f"Assigned Tools: {assigned_tools}")
        
        # Prepare context from state
        context = _prepare_task_context(state)
        logger.info(f"Prepared context: {context}")
        
        # Define success criteria
        success_criteria = _define_success_criteria(current_task, state)
        logger.info(f"Success criteria: {success_criteria}")
        
        # Execute the task using task_tool
        logger.info("Invoking task_tool to execute task...")
        execution_result = _execute_task_with_tool(
            task_description=task_description,
            assigned_tools=assigned_tools,
            context=context,
            success_criteria=success_criteria
        )
        
        # Update state with execution results
        updated_state = _update_state_with_results(
            state=state,
            task_id=task_id,
            task_description=task_description,
            execution_result=execution_result
        )
        
        logger.info("Task execution completed successfully")
        return updated_state
        
    except Exception as e:
        logger.error(f"Error in execute_task_node: {e}")
        # Add error message to state
        state["messages"].append(AIMessage(content=f"Task execution error: {str(e)}"))
        return state


def _prepare_task_context(state: AgentState) -> Dict[str, Any]:
    """
    Prepare context for task execution from current state.
    
    Args:
        state: Current agent state
        
    Returns:
        Context dictionary for task execution
    """
    context = {
        "objective": state.get("objective", ""),
        "iteration_count": state.get("iteration_count", 0),
        "completed_tasks_count": len(state.get("completed_tasks", [])),
        "pending_tasks_count": len([t for t in state.get("todo_list", []) if t.get("status") == "pending"])
    }
    
    # Add relevant completed tasks
    completed_tasks = state.get("completed_tasks", [])
    if completed_tasks:
        context["recent_completed_tasks"] = [
            {
                "description": task.get("task", task.get("description", "")),
                "result": task.get("result", ""),
                "artifacts": task.get("artifacts", [])
            }
            for task in completed_tasks[-3:]  # Last 3 completed tasks
        ]
    
    # Add any existing artifacts/files
    context["existing_artifacts"] = _get_existing_artifacts(state)
    
    logger.info(f"Prepared context with {len(context)} items")
    return context


def _define_success_criteria(current_task: Dict[str, Any], state: AgentState) -> str:
    """
    Define success criteria for the current task.
    
    Args:
        current_task: Current task to execute
        state: Current agent state
        
    Returns:
        Success criteria string
    """
    task_description = current_task.get("description", "")
    assigned_tools = current_task.get("assigned_tools", [])
    
    # Base success criteria
    success_criteria = f"Complete the task: {task_description}"
    
    # Add tool-specific success criteria
    if "execute_code_tool" in assigned_tools:
        success_criteria += " and provide the execution results"
    
    if "write_file_tool" in assigned_tools:
        success_criteria += " and save any important results to files"
    
    if "search_internet_tool" in assigned_tools:
        success_criteria += " and provide relevant information found"
    
    if "web_scrape_tool" in assigned_tools:
        success_criteria += " and extract the requested content"
    
    # Add general success criteria
    success_criteria += ". Ensure the task is completed successfully and any artifacts are created as needed."
    
    return success_criteria


def _execute_task_with_tool(
    task_description: str,
    assigned_tools: List[str],
    context: Dict[str, Any],
    success_criteria: str
) -> Dict[str, Any]:
    """
    Execute the task using the task_tool.
    
    Args:
        task_description: Description of the task to execute
        assigned_tools: List of tools assigned to the task
        context: Context for task execution
        success_criteria: Success criteria for the task
        
    Returns:
        Execution result dictionary
    """
    try:
        logger.info("Invoking task_tool with parameters:")
        logger.info(f"  Task: {task_description}")
        logger.info(f"  Tools: {assigned_tools}")
        logger.info(f"  Context keys: {list(context.keys())}")
        logger.info(f"  Success criteria: {success_criteria[:100]}...")
        
        # Invoke the task_tool
        result = task_tool.invoke({
            "task_description": task_description,
            "assigned_tools": assigned_tools,
            "context": context,
            "success_criteria": success_criteria
        })
        
        logger.info(f"Task execution result: {result.get('success', False)}")
        logger.info(f"Result details: {result.get('details', 'No details')[:200]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing task with tool: {e}")
        return {
            "success": False,
            "result": f"Task execution failed: {str(e)}",
            "artifacts": [],
            "details": f"Error: {str(e)}"
        }


def _update_state_with_results(
    state: AgentState,
    task_id: int,
    task_description: str,
    execution_result: Dict[str, Any]
) -> AgentState:
    """
    Update state with task execution results.
    
    Args:
        state: Current agent state
        task_id: ID of the executed task
        task_description: Description of the executed task
        execution_result: Result from task execution
        
    Returns:
        Updated agent state
    """
    logger.info("Updating state with execution results...")
    
    # Determine task status
    task_status = TASK_STATUS_COMPLETED if execution_result.get("success", False) else TASK_STATUS_FAILED
    
    # Create completed task entry
    completed_task = {
        "id": task_id,
        "task": task_description,
        "result": execution_result.get("result", ""),
        "artifacts": execution_result.get("artifacts", []),
        "status": task_status,
        "execution_details": execution_result.get("details", ""),
        "completed_iteration": state.get("iteration_count", 0)
    }
    
    # Add to completed tasks
    if "completed_tasks" not in state:
        state["completed_tasks"] = []
    state["completed_tasks"].append(completed_task)
    
    # Remove from TODO list
    if "todo_list" in state:
        state["todo_list"] = [
            task for task in state["todo_list"] 
            if task.get("id") != task_id
        ]
    
    # Clear current task
    state["current_task"] = None
    
    # Add execution result to messages
    if execution_result.get("success", False):
        success_message = f"✅ Task {task_id} completed successfully: {task_description}"
        if execution_result.get("artifacts"):
            success_message += f" (Created {len(execution_result['artifacts'])} artifacts)"
        state["messages"].append(AIMessage(content=success_message))
    else:
        error_message = f"❌ Task {task_id} failed: {task_description}"
        if execution_result.get("details"):
            error_message += f" - {execution_result['details']}"
        state["messages"].append(AIMessage(content=error_message))
    
    logger.info(f"Task {task_id} marked as {task_status}")
    logger.info(f"Completed tasks count: {len(state.get('completed_tasks', []))}")
    logger.info(f"Remaining TODO tasks: {len(state.get('todo_list', []))}")
    
    return state


def _get_existing_artifacts(state: AgentState) -> List[str]:
    """
    Get list of existing artifacts from completed tasks.
    
    Args:
        state: Current agent state
        
    Returns:
        List of artifact file paths
    """
    artifacts = []
    completed_tasks = state.get("completed_tasks", [])
    
    for task in completed_tasks:
        task_artifacts = task.get("artifacts", [])
        if isinstance(task_artifacts, list):
            artifacts.extend(task_artifacts)
        elif isinstance(task_artifacts, str):
            artifacts.append(task_artifacts)
    
    logger.info(f"Found {len(artifacts)} existing artifacts")
    return artifacts


def validate_task_execution(state: AgentState) -> bool:
    """
    Validate that task execution can proceed.
    
    Args:
        state: Current agent state
        
    Returns:
        True if task execution can proceed, False otherwise
    """
    # Check if there's a current task
    current_task = state.get("current_task")
    if not current_task:
        logger.warning("No current task to execute")
        return False
    
    # Check if task has required fields
    required_fields = ["id", "description", "assigned_tools"]
    missing_fields = [field for field in required_fields if not current_task.get(field)]
    
    if missing_fields:
        logger.warning(f"Current task missing required fields: {missing_fields}")
        return False
    
    # Check if assigned tools are valid
    assigned_tools = current_task.get("assigned_tools", [])
    if not assigned_tools:
        logger.warning("No tools assigned to current task")
        return False
    
    logger.info("Task execution validation passed")
    return True


def get_task_execution_summary(state: AgentState) -> Dict[str, Any]:
    """
    Get a summary of task execution status.
    
    Args:
        state: Current agent state
        
    Returns:
        Summary dictionary
    """
    completed_tasks = state.get("completed_tasks", [])
    todo_list = state.get("todo_list", [])
    pending_tasks = [task for task in todo_list if task.get("status") == "pending"]
    
    successful_tasks = [task for task in completed_tasks if task.get("status") == TASK_STATUS_COMPLETED]
    failed_tasks = [task for task in completed_tasks if task.get("status") == TASK_STATUS_FAILED]
    
    total_artifacts = sum(len(task.get("artifacts", [])) for task in completed_tasks)
    
    summary = {
        "total_tasks": len(completed_tasks) + len(pending_tasks),
        "completed_tasks": len(completed_tasks),
        "successful_tasks": len(successful_tasks),
        "failed_tasks": len(failed_tasks),
        "pending_tasks": len(pending_tasks),
        "total_artifacts": total_artifacts,
        "completion_rate": len(completed_tasks) / max(1, len(completed_tasks) + len(pending_tasks)) * 100,
        "success_rate": len(successful_tasks) / max(1, len(completed_tasks)) * 100
    }
    
    logger.info(f"Task execution summary: {summary}")
    return summary


# ============================================================================
# UTILITY FUNCTIONS FOR TASK EXECUTION
# ============================================================================

def create_task_execution_context(
    objective: str,
    completed_tasks: List[Dict[str, Any]],
    current_iteration: int
) -> Dict[str, Any]:
    """
    Create a standardized context for task execution.
    
    Args:
        objective: Main objective being worked on
        completed_tasks: List of completed tasks
        current_iteration: Current iteration number
        
    Returns:
        Standardized context dictionary
    """
    context = {
        "objective": objective,
        "iteration": current_iteration,
        "completed_tasks_count": len(completed_tasks),
        "recent_findings": []
    }
    
    # Add recent findings from completed tasks
    for task in completed_tasks[-3:]:  # Last 3 tasks
        if task.get("result"):
            context["recent_findings"].append({
                "task": task.get("task", ""),
                "result": task.get("result", "")[:200]  # Truncate for context
            })
    
    return context


def format_task_execution_result(
    task_id: int,
    task_description: str,
    execution_result: Dict[str, Any]
) -> str:
    """
    Format task execution result for logging and display.
    
    Args:
        task_id: ID of the executed task
        task_description: Description of the task
        execution_result: Result from task execution
        
    Returns:
        Formatted result string
    """
    success = execution_result.get("success", False)
    status = "✅ SUCCESS" if success else "❌ FAILED"
    
    result_text = f"Task {task_id}: {status}\n"
    result_text += f"Description: {task_description}\n"
    
    if execution_result.get("result"):
        result_text += f"Result: {execution_result['result'][:200]}...\n"
    
    if execution_result.get("artifacts"):
        result_text += f"Artifacts: {len(execution_result['artifacts'])} files created\n"
    
    if execution_result.get("details"):
        result_text += f"Details: {execution_result['details'][:100]}...\n"
    
    return result_text

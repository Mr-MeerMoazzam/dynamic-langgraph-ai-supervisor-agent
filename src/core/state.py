"""
State schema for the Supervisor Agent system.

This module defines the AgentState TypedDict that represents the complete state
of the supervisor agent throughout its execution lifecycle. The state tracks
the conversation history, current objectives, task decomposition, progress,
and final results.

The state is designed to be immutable and accumulated through LangGraph's
state management system, ensuring thread-safe and predictable state transitions.
"""

from typing import TypedDict, Annotated, List, Dict, Union, Optional
import operator
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    Complete state representation for the Supervisor Agent system.

    This TypedDict defines all the state that flows through the LangGraph
    execution graph, enabling the supervisor to track progress, maintain
    conversation context, and coordinate subagent execution.

    The state is designed to be accumulated rather than replaced, with
    specific fields using the `operator.add` annotation for list concatenation.
    """

    messages: Annotated[List[BaseMessage], operator.add]
    """
    Conversation history and message accumulation.

    This field accumulates all messages exchanged between the user, supervisor,
    and subagents throughout the execution. Each interaction appends to this
    list, providing complete conversation context for decision-making.

    Uses operator.add to concatenate message lists from different graph nodes.
    """

    objective: str
    """
    The original user-provided goal or objective.

    This field contains the initial user request that the supervisor agent
    must decompose and execute. It remains constant throughout the execution
    and serves as the reference point for all planning and decision-making.
    """

    todo_list: List[Dict[str, Union[int, str, List[str]]]]
    """
    Dynamic task decomposition and planning.

    This field contains the current list of tasks that need to be completed
    to achieve the objective. Each task is represented as a dictionary with:

    - id: Unique integer identifier for the task
    - task: Human-readable description of what needs to be done
    - status: Current status (pending, in_progress, completed, failed)
    - assigned_tools: List of tool names assigned to this specific task

    The supervisor maintains and updates this list as tasks are completed
    and new tasks are discovered through subagent execution.
    """

    completed_tasks: List[Dict[str, Union[int, str, List[str], Dict]]]
    """
    Completed tasks with their results and metadata.

    This field accumulates all tasks that have been successfully completed,
    including their original definition and execution results. Each completed
    task includes:

    - id: The original task ID from todo_list
    - task: The original task description
    - status: Final status (always "completed" for items in this list)
    - assigned_tools: Tools that were used for this task
    - result: Execution results, artifacts, or findings from the task
    - execution_time: Time taken to complete the task
    - subagent_logs: Logs from the subagent that executed this task

    This serves as both a record of completed work and a knowledge base
    for subsequent tasks.
    """

    current_task: Optional[Dict[str, Union[int, str, List[str]]]]
    """
    The task currently being executed by a subagent.

    This field contains the task that is currently assigned to a subagent
    for execution. When no task is being executed, this is None.

    The structure mirrors todo_list entries:
    - id: Task identifier
    - task: Task description
    - status: Current status (should be "in_progress" when assigned)
    - assigned_tools: Tools assigned to this task
    """

    iteration_count: int
    """
    Safety counter to prevent infinite loops.

    This counter increments with each iteration of the supervisor loop.
    When it reaches MAX_ITERATIONS, the supervisor should terminate
    execution to prevent infinite loops or stuck states.

    Starts at 0 and increments with each supervisor decision cycle.
    """

    final_result: Optional[str]
    """
    The final output when the objective is completed.

    This field contains the consolidated result when the supervisor
    determines that the objective has been successfully completed.
    It may include summaries, reports, or other artifacts generated
    from the completed tasks.

    Is None until the supervisor decides the objective is complete.
    """


def create_initial_state(objective: str) -> AgentState:
    """
    Create the initial state for a new agent execution.

    This function initializes all state fields with appropriate starting values
    for a new objective. The state is ready for the supervisor to begin
    decomposing the objective into tasks.

    Args:
        objective: The user's goal or request that the agent should achieve

    Returns:
        AgentState: A complete initial state with all fields populated

    Example:
        >>> state = create_initial_state("Analyze the quarterly sales data")
        >>> state["objective"]
        'Analyze the quarterly sales data'
        >>> state["iteration_count"]
        0
        >>> len(state["todo_list"])
        0
    """
    return AgentState(
        messages=[],
        objective=objective,
        todo_list=[],
        completed_tasks=[],
        current_task=None,
        iteration_count=0,
        final_result=None,
    )


# Constants for task status management
MAX_ITERATIONS = 20
"""
Maximum number of supervisor iterations before forced termination.

This safety limit prevents infinite loops in case the supervisor gets
stuck in a planning loop or fails to make progress toward the objective.
"""

TASK_STATUS_PENDING = "pending"
"""
Task status indicating the task is waiting to be assigned to a subagent.

Tasks in this state are available for the supervisor to assign based
on dependencies and available resources.
"""

TASK_STATUS_IN_PROGRESS = "in_progress"
"""
Task status indicating the task is currently being executed by a subagent.

Only one task should be in this state at a time, representing the
currently active execution.
"""

TASK_STATUS_COMPLETED = "completed"
"""
Task status indicating the task has been successfully completed.

Completed tasks are moved from todo_list to completed_tasks with
their results and metadata.
"""

TASK_STATUS_FAILED = "failed"
"""
Task status indicating the task execution failed.

Failed tasks remain in todo_list but are marked as failed. The
supervisor may retry failed tasks or mark the entire objective
as failed depending on the nature of the failure.
"""


# Type aliases for better code readability
TaskDict = Dict[str, Union[int, str, List[str]]]
"""
Type alias for task dictionary structure used in todo_list and current_task.

This represents a single task with its id, description, status, and assigned tools.
"""

CompletedTaskDict = Dict[str, Union[int, str, List[str], Dict]]
"""
Type alias for completed task dictionary structure used in completed_tasks.

This extends TaskDict with additional fields for results, execution metadata,
and subagent logs.
"""

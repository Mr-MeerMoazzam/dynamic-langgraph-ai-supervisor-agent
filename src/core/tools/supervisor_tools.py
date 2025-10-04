"""
Supervisor tools for the Supervisor Agent system.

This module contains tools specifically designed for the Supervisor component
of the agent system, including todo list management and task coordination.
"""

from typing import List, Dict, Any, Optional, Literal
from langchain.tools import tool
from dataclasses import dataclass, field
import logging

# Import subagent executor
from src.core.agents.subagent import SubagentExecutor

# Set up logger
logger = logging.getLogger(__name__)


@dataclass
class TodoManager:
    """
    Manages the todo list state for the Supervisor Agent.

    This class maintains and manages the todo list state, providing methods
    to create, add, and update tasks. It's designed to work with LangGraph's
    state management system.
    """

    todo_list: List[Dict[str, Any]] = field(default_factory=list)
    next_task_id: int = 1

    def create_tasks(self, task_descriptions: List[str], assigned_tools: List[str] = None) -> List[Dict[str, Any]]:
        """
        Create initial todo list from task descriptions.

        Args:
            task_descriptions: List of task description strings
            assigned_tools: Tools to assign to all tasks (optional)

        Returns:
            List of created task dictionaries
        """
        created_tasks = []
        for description in task_descriptions:
            if description.strip():  # Skip empty descriptions
                # Analyze task and assign appropriate tools
                task_tools = self._analyze_task_tools(description.strip(), assigned_tools)
                
                task = {
                    "id": self.next_task_id,
                    "task": description.strip(),
                    "status": "pending",
                    "assigned_tools": task_tools
                }
                self.todo_list.append(task)
                created_tasks.append(task)
                self.next_task_id += 1

        return created_tasks
    
    def _analyze_task_tools(self, task_description: str, default_tools: List[str] = None) -> List[str]:
        """
        Analyze a task description and assign appropriate tools.
        
        Args:
            task_description: The task description to analyze
            default_tools: Default tools to use if no specific analysis
            
        Returns:
            List of appropriate tools for this task
        """
        task_lower = task_description.lower()
        
        # Tool assignment logic based on task content
        tools = []
        
        # Code execution tasks - more precise logic
        code_keywords = ['calculate', 'compute', 'algorithm', 'formula', 'math', 'number', 'sequence']
        # Only add execute_code if task explicitly needs calculation AND not just reading/writing
        if any(keyword in task_lower for keyword in code_keywords):
            tools.append('execute_code')
        # For fibonacci/sum, only add execute_code if it's a calculation task, not a report task
        elif any(keyword in task_lower for keyword in ['fibonacci', 'sum', 'total']):
            # Check if it's a report/summary task (don't need execute_code for those)
            is_report_task = any(report_word in task_lower for report_word in ['report', 'summary', 'show', 'display'])
            if not is_report_task:
                tools.append('execute_code')
        
        # File writing tasks
        if any(keyword in task_lower for keyword in ['save', 'write', 'create file', 'store', 'output to file', 'save to']):
            tools.append('write_file')
        
        # File reading tasks - ENHANCED LOGIC
        read_keywords = [
            'read', 'load', 'open file', 'from file', 'read file',
            # NEW: Tasks that likely need to read previous outputs
            'summary', 'report', 'show', 'display', 'based on', 'using',
            'from', 'with', 'containing', 'including', 'combine', 'merge'
        ]
        if any(keyword in task_lower for keyword in read_keywords):
            tools.append('read_file')
        
        # File editing tasks
        if any(keyword in task_lower for keyword in ['edit', 'modify', 'update file', 'change']):
            tools.append('edit_file')
        
        # Web search tasks
        if any(keyword in task_lower for keyword in ['search', 'find', 'look up', 'research', 'web', 'internet']):
            tools.append('search_internet')
        
        # Web scraping tasks - more precise logic
        if any(keyword in task_lower for keyword in ['scrape', 'extract from', 'crawl', 'get content from url']):
            tools.append('web_scrape')
        
        # If no specific tools identified, use default or minimal set
        if not tools:
            if default_tools:
                tools = default_tools
            else:
                # Default minimal toolset
                tools = ['execute_code'] if 'calculate' in task_lower else ['write_file']
        
        return tools

    def add_task(self, description: str, assigned_tools: List[str] = None) -> Dict[str, Any]:
        """
        Add a new task to the existing todo list.

        Args:
            description: Task description string
            assigned_tools: Tools to assign to this task (optional)

        Returns:
            The created task dictionary
        """
        # Analyze task and assign appropriate tools
        task_tools = self._analyze_task_tools(description.strip(), assigned_tools)
        
        task = {
            "id": self.next_task_id,
            "task": description.strip(),
            "status": "pending",
            "assigned_tools": task_tools
        }
        self.todo_list.append(task)
        self.next_task_id += 1
        return task

    def update_task_status(self, task_id: int, new_status: str) -> Optional[Dict[str, Any]]:
        """
        Update the status of a specific task.

        Args:
            task_id: ID of the task to update
            new_status: New status value

        Returns:
            Updated task dictionary or None if task not found
        """
        # Validate status
        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid_statuses}")

        # Find and update task
        for task in self.todo_list:
            if task["id"] == task_id:
                task["status"] = new_status
                return task

        return None  # Task not found

    def update_task_with_artifacts(self, task_id: int, new_status: str, artifacts: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Update the status and artifacts of a specific task.

        Args:
            task_id: ID of the task to update
            new_status: New status value
            artifacts: List of files created by this task

        Returns:
            Updated task dictionary or None if task not found
        """
        # Validate status
        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid_statuses}")

        # Find and update task
        for task in self.todo_list:
            if task["id"] == task_id:
                task["status"] = new_status
                if artifacts is not None:
                    task["artifacts"] = artifacts
                return task

        return None  # Task not found

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks with 'pending' status."""
        return [task for task in self.todo_list if task["status"] == "pending"]

    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        for task in self.todo_list:
            if task["id"] == task_id:
                return task
        return None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return self.todo_list.copy()

    def clear_completed_tasks(self) -> int:
        """Remove all completed tasks and return count removed."""
        initial_count = len(self.todo_list)
        self.todo_list = [task for task in self.todo_list if task["status"] != "completed"]
        return initial_count - len(self.todo_list)


# Global todo manager instance (in production, this would be managed by state)
todo_manager = TodoManager()


@tool
def update_todo_tool(
    action: Literal["create", "update_status", "add_new"],
    task_id: Optional[int] = None,
    task_description: Optional[str] = None,
    new_status: Optional[str] = None,
    assigned_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Update and manage the Supervisor Agent's todo list.

    This tool allows the Supervisor to create, modify, and track tasks in the
    todo list. It's essential for task decomposition, progress tracking, and
    coordinating subagent execution.

    Use this tool when the Supervisor needs to:
    - Initialize the todo list from a complex objective
    - Add new tasks discovered during execution
    - Update task status as work progresses
    - Track which tools are assigned to each task

    Args:
        action: The action to perform:
            - "create": Initialize todo list from task_description (can be multi-line)
            - "add_new": Add a new task to existing list
            - "update_status": Update status of task with task_id
        task_id: ID of task to update (required for "update_status")
        task_description: Task description (required for "create" and "add_new")
        new_status: New status for task (required for "update_status")
        assigned_tools: List of tool names to assign to task(s)

    Returns:
        Dict containing:
        - success: Boolean indicating if operation succeeded
        - message: Human-readable status message
        - todo_list: Current complete todo list after operation

    Status Values:
        - "pending": Task is waiting to be assigned
        - "in_progress": Task is currently being executed
        - "completed": Task finished successfully
        - "failed": Task execution failed

    Examples:
        >>> # Create initial todo list from multi-line description
        >>> result = update_todo_tool(
        ...     action="create",
        ...     task_description="1. Research market trends\\n2. Analyze competitor data\\n3. Generate report",
        ...     assigned_tools=["search_internet", "web_scrape"]
        ... )

        >>> # Add a new task
        >>> result = update_todo_tool(
        ...     action="add_new",
        ...     task_description="Create summary presentation",
        ...     assigned_tools=["execute_code"]
        ... )

        >>> # Update task status
        >>> result = update_todo_tool(
        ...     action="update_status",
        ...     task_id=1,
        ...     new_status="completed"
        ... )
    """
    try:
        # Auto-correct tool names at the source to prevent runtime corrections
        if assigned_tools:
            tool_name_corrections = {
                "execute_code_tool": "execute_code",
                "search_internet_tool": "search_internet", 
                "web_scrape_tool": "web_scrape",
                "read_file_tool": "read_file",
                "write_file_tool": "write_file",
                "edit_file_tool": "edit_file"
            }
            
            corrected_tools = []
            for tool in assigned_tools:
                if tool in tool_name_corrections:
                    corrected_tool = tool_name_corrections[tool]
                    corrected_tools.append(corrected_tool)
                    logger.info(f"Pre-corrected tool name: '{tool}' → '{corrected_tool}'")
                else:
                    corrected_tools.append(tool)
            
            assigned_tools = corrected_tools
        
        if action == "create":
            # Create initial todo list from description
            if not task_description:
                return {
                    "success": False,
                    "message": "task_description is required for 'create' action",
                    "todo_list": todo_manager.get_all_tasks()
                }

            # Split multi-line description into individual tasks
            task_descriptions = [line.strip() for line in task_description.split('\n') if line.strip()]

            if not task_descriptions:
                return {
                    "success": False,
                    "message": "No valid tasks found in task_description",
                    "todo_list": todo_manager.get_all_tasks()
                }

            # Create tasks
            created_tasks = todo_manager.create_tasks(task_descriptions, assigned_tools)

            return {
                "success": True,
                "message": f"Created {len(created_tasks)} tasks from description",
                "todo_list": todo_manager.get_all_tasks()
            }

        elif action == "add_new":
            # Add a new task
            if not task_description:
                return {
                    "success": False,
                    "message": "task_description is required for 'add_new' action",
                    "todo_list": todo_manager.get_all_tasks()
                }

            new_task = todo_manager.add_task(task_description, assigned_tools)

            return {
                "success": True,
                "message": f"Added new task: {new_task['task'][:50]}...",
                "todo_list": todo_manager.get_all_tasks()
            }

        elif action == "update_status":
            # Update task status
            if task_id is None:
                return {
                    "success": False,
                    "message": "task_id is required for 'update_status' action",
                    "todo_list": todo_manager.get_all_tasks()
                }

            if new_status is None:
                return {
                    "success": False,
                    "message": "new_status is required for 'update_status' action",
                    "todo_list": todo_manager.get_all_tasks()
                }

            updated_task = todo_manager.update_task_status(task_id, new_status)

            if updated_task:
                return {
                    "success": True,
                    "message": f"Updated task {task_id} status to {new_status}",
                    "todo_list": todo_manager.get_all_tasks()
                }
            else:
                return {
                    "success": False,
                    "message": f"Task with ID {task_id} not found",
                    "todo_list": todo_manager.get_all_tasks()
                }

        else:
            return {
                "success": False,
                "message": f"Invalid action '{action}'. Must be 'create', 'add_new', or 'update_status'",
                "todo_list": todo_manager.get_all_tasks()
            }

    except ValueError as e:
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "todo_list": todo_manager.get_all_tasks()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "todo_list": todo_manager.get_all_tasks()
        }


@tool
def task_tool(
    task_description: str,
    assigned_tools: List[str],
    success_criteria: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create and execute a specialized subagent for a specific task.

    This tool serves as the primary interface between the Supervisor and SubagentExecutor,
    enabling the Supervisor to dynamically create and run specialized subagents for
    complex task decomposition and execution.

    Use this tool when the Supervisor needs to:
    - Execute a specific task that requires specialized capabilities
    - Leverage different tool combinations for different objectives
    - Maintain context and state across subagent executions
    - Track artifacts and results from subagent work

    Args:
        task_description: Clear description of what the subagent should accomplish
        assigned_tools: List of tool names to assign to this subagent (must be valid)
        context: Dictionary containing relevant information from previous tasks,
                supervisor decisions, or other contextual data
        success_criteria: Specific criteria that define when the task is complete

    Returns:
        Dict containing:
        - success: Boolean indicating if subagent execution completed successfully
        - result: Final output/result from the subagent
        - artifacts: List of files created by the subagent during execution
        - details: Additional information about execution (iterations used, etc.)

    Tool Validation:
        - Validates that all assigned_tools are available in the system
        - Ensures task_description is not empty
        - Verifies context is a dictionary (can be empty)
        - Validates success_criteria is provided

    Assigned Tools Examples:
        - ["execute_code"] - For computational tasks
        - ["search_internet", "web_scrape"] - For research tasks
        - ["read_file", "write_file"] - For file-based tasks
        - ["execute_code", "write_file"] - For code execution with output

    Context Structure:
        - Should contain relevant information from previous tasks
        - Can include file paths, findings, or other metadata
        - Example: {"previous_findings": "Sales increased 15%", "data_file": "sales.csv"}

    Success Criteria Examples:
        - "Generate a summary report in report.txt"
        - "Calculate the fibonacci sequence up to n=20"
        - "Extract key insights from the provided data"

    Example:
        >>> result = task_tool(
        ...     task_description="Analyze quarterly sales data trends",
        ...     assigned_tools=["read_file", "execute_code", "write_file"],
        ...     context={"data_file": "sales_q4.csv", "previous_quarter": "Q3 results"},
        ...     success_criteria="Generate analysis_report.txt with key findings"
        ... )
    """
    try:
        # Provide default context if none provided
        if context is None:
            context = {
                "objective": "Execute the assigned task",
                "iteration": 1,
                "completed_tasks_count": 0,
                "recent_findings": []
            }
        
        # Validate inputs
        if not task_description or not isinstance(task_description, str):
            return {
                "success": False,
                "result": "",
                "artifacts": [],
                "details": "task_description must be a non-empty string"
            }

        if not assigned_tools or not isinstance(assigned_tools, list):
            return {
                "success": False,
                "result": "",
                "artifacts": [],
                "details": "assigned_tools must be a non-empty list"
            }

        if not isinstance(context, dict):
            return {
                "success": False,
                "result": "",
                "artifacts": [],
                "details": "context must be a dictionary"
            }

        if not success_criteria or not isinstance(success_criteria, str):
            return {
                "success": False,
                "result": "",
                "artifacts": [],
                "details": "success_criteria must be a non-empty string"
            }

        # Auto-correct common tool name mistakes
        tool_name_corrections = {
            "execute_code_tool": "execute_code",
            "search_internet_tool": "search_internet", 
            "web_scrape_tool": "web_scrape",
            "read_file_tool": "read_file",
            "write_file_tool": "write_file",
            "edit_file_tool": "edit_file"
        }
        
        # Apply corrections
        corrected_tools = []
        for tool in assigned_tools:
            if tool in tool_name_corrections:
                corrected_tool = tool_name_corrections[tool]
                corrected_tools.append(corrected_tool)
                logger.info(f"Auto-corrected tool name: '{tool}' → '{corrected_tool}'")
            else:
                corrected_tools.append(tool)
        
        assigned_tools = corrected_tools

        # Validate assigned_tools are available (file tools + assignable tools)
        from src.core.tools.assignable_tools import get_assignable_tools
        from src.core.tools.file_tools import get_file_tools

        assignable_tools = get_assignable_tools()
        file_tools = get_file_tools()
        available_tools = {**assignable_tools, **file_tools}

        invalid_tools = [tool for tool in assigned_tools if tool not in available_tools]
        if invalid_tools:
            return {
                "success": False,
                "result": "",
                "artifacts": [],
                "details": f"Invalid tools: {invalid_tools}. Available tools: {list(available_tools.keys())}"
            }

        # Create and run subagent
        executor = SubagentExecutor()

        subagent_result = executor.run_subagent(
            task_description=task_description,
            assigned_tools=assigned_tools,  # Pass tool names, subagent will look them up
            context=context,
            success_criteria=success_criteria,
            max_iterations=15  # Default max iterations
        )

        # Update task status in TODO list with artifacts
        # Find the task in todo_list and update its status
        task_updated = False
        all_tasks = todo_manager.get_all_tasks()
        for task in all_tasks:
            if task.get("task") == task_description or task.get("description") == task_description:
                artifacts = subagent_result.get("artifacts_created", [])
                if subagent_result["success"]:
                    todo_manager.update_task_with_artifacts(task["id"], "completed", artifacts)
                    logger.info(f"✅ Updated task {task['id']} to completed with artifacts: {artifacts}")
                else:
                    todo_manager.update_task_with_artifacts(task["id"], "failed", artifacts)
                    logger.info(f"❌ Updated task {task['id']} to failed with artifacts: {artifacts}")
                task_updated = True
                break
        
        if not task_updated:
            # Improved logging with better truncation and fuzzy matching
            logger.warning(f"⚠️ Could not find exact task match for: {task_description[:100]}...")
            
            # Show available tasks with better truncation
            available_task_previews = []
            for t in all_tasks:
                task_text = t.get('task', 'NO_TASK')
                preview = task_text[:80] + "..." if len(task_text) > 80 else task_text
                available_task_previews.append(f"ID:{t.get('id', '?')} - {preview}")
            
            logger.warning(f"Available tasks ({len(all_tasks)} total):")
            for preview in available_task_previews:
                logger.warning(f"  {preview}")
            
            # Try fuzzy matching for better debugging
            from difflib import get_close_matches
            close_matches = get_close_matches(
                task_description, 
                [t.get('task', '') for t in all_tasks], 
                n=3, 
                cutoff=0.6
            )
            if close_matches:
                logger.warning(f"Close matches found: {close_matches}")
        
        # Format response
        return {
            "success": subagent_result["success"],
            "result": subagent_result["result"],
            "artifacts": subagent_result["artifacts_created"],
            "details": f"Used {subagent_result['iterations_used']} iterations",
            "task_updated": task_updated
        }

    except Exception as e:
        return {
            "success": False,
            "result": f"Task execution failed: {str(e)}",
            "artifacts": [],
            "details": f"Error type: {type(e).__name__}"
        }


def get_supervisor_tools() -> List[Any]:
    """
    Get all supervisor tools for use in the Supervisor Agent.

    This function returns a list of all tools specifically designed for
    the Supervisor component, including todo management, subagent execution,
    and file operations for coordination.

    Returns:
        List[Any]: List containing supervisor tools in recommended order:
        - update_todo_tool: For todo list management
        - task_tool: For subagent execution
        - File tools: For reading subagent results and coordination

    Example:
        >>> tools = get_supervisor_tools()
        >>> print([tool.name for tool in tools])
        # ['update_todo_tool', 'task_tool', 'read_file_tool', 'write_file_tool', 'edit_file_tool']
    """
    from src.core.tools.file_tools import get_file_tools
    
    # Get supervisor-specific tools
    supervisor_tools = [
        update_todo_tool,
        task_tool
    ]
    
    # Add file tools for coordination
    file_tools = get_file_tools()
    supervisor_tools.extend(file_tools.values())
    
    return supervisor_tools

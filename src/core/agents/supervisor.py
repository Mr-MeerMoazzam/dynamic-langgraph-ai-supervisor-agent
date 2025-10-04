"""
Supervisor Agent implementation for the LangGraph-based Supervisor system.

This module contains the SupervisorAgent class and supervisor_node function that
orchestrate the entire system by analyzing state, making decisions, and coordinating
subagents to achieve complex objectives.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, SystemMessage

from src.core.state import AgentState, MAX_ITERATIONS, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED
from src.core.prompts import SUPERVISOR_SYSTEM_PROMPT, format_supervisor_prompt
from src.core.tools.supervisor_tools import get_supervisor_tools

# Configure logging
logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    The Supervisor agent that orchestrates the entire system.
    
    The Supervisor analyzes the current state, makes decisions about what actions
    to take next, and coordinates subagents to execute tasks. It's the central
    intelligence that drives the system forward.
    """
    
    def __init__(self, llm: ChatOpenAI, tools: List[Tool]):
        """
        Initialize the Supervisor agent.
        
        Args:
            llm: Language model for decision making
            tools: List of tools available to the supervisor
        """
        self.llm = llm
        self.tools = tools
        self.agent_executor = None
        self._setup_agent()
        
        logger.info(f"SupervisorAgent initialized with {len(tools)} tools")
    
    def _setup_agent(self):
        """Setup the agent executor with tools and prompt."""
        try:
            # Create the agent with tools
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=ChatPromptTemplate.from_messages([
                    ("system", SUPERVISOR_SYSTEM_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])
            )
            
            # Create agent executor with memory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True,
                max_iterations=50,  # Increased to allow multiple task executions
                max_execution_time=300,  # 5 minutes timeout
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            logger.info("Supervisor agent executor setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup supervisor agent: {e}")
            raise
    
    def decide_next_action(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze current state and decide the next action.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with action, reasoning, and next_task_id
        """
        try:
            # Get current state info
            todo_list = state.get("todo_list", [])
            iteration_count = state.get("iteration_count", 0)
            
            # Count task statuses for debugging
            pending_tasks = [task for task in todo_list if task.get("status") == TASK_STATUS_PENDING]
            completed_tasks = [task for task in todo_list if task.get("status") == TASK_STATUS_COMPLETED]
            failed_tasks = [task for task in todo_list if task.get("status") == "failed"]
            
            logger.info(f"🔍 DECIDE_NEXT_ACTION DEBUG:")
            logger.info(f"   TODO Status: {len(pending_tasks)} pending, {len(completed_tasks)} completed, {len(failed_tasks)} failed out of {len(todo_list)} total")
            logger.info(f"   Current iteration: {iteration_count}")
            logger.info(f"   Pending tasks: {[t.get('task', 'NO_TASK')[:30] for t in pending_tasks]}")
            logger.info(f"   Completed tasks: {[t.get('task', 'NO_TASK')[:30] for t in completed_tasks]}")
            
            # Check for termination conditions
            if iteration_count >= MAX_ITERATIONS:
                logger.info("Maximum iterations reached, finalizing")
                return {
                    "action": "finalize",
                    "reasoning": f"Maximum iterations ({MAX_ITERATIONS}) reached",
                    "next_task_id": None
                }
            
            # If no tasks exist and first iteration, need to plan
            if len(todo_list) == 0 and iteration_count == 1:
                logger.info("🔍 DECISION: No tasks exist, need to create initial plan")
                return {
                    "action": "plan",
                    "reasoning": "No tasks exist, need to create initial plan",
                    "next_task_id": None
                }
            
            # If has pending tasks, execute next one
            if pending_tasks:
                next_task = pending_tasks[0]  # Take first pending task
                logger.info(f"🔍 DECISION: Executing next task: {next_task.get('id')} - {next_task.get('task', 'Unknown task')}")
                return {
                    "action": "execute",
                    "reasoning": f"Execute task {next_task.get('id')}: {next_task.get('task', 'Unknown task')}",
                    "next_task_id": next_task.get("id")
                }
            
            # All tasks complete
            logger.info("🔍 DECISION: All tasks completed, finalizing")
            return {
                "action": "finalize",
                "reasoning": "All tasks completed successfully",
                "next_task_id": None
            }
            
        except Exception as e:
            logger.error(f"Error in decide_next_action: {e}")
            return {
                "action": "finalize",
                "reasoning": f"Error occurred: {str(e)}",
                "next_task_id": None
            }
    
    def execute_action(self, state: AgentState, action: str, task_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute the decided action using programmatic routing.
        
        Args:
            state: Current agent state
            action: Action to execute ("plan", "execute", "finalize")
            task_id: ID of task to execute (if applicable)
            
        Returns:
            Dictionary with execution results
        """
        try:
            logger.info(f"🎯 EXECUTING PROGRAMMATIC ACTION: {action}")
            
            if action == "finalize":
                return self._execute_finalize(state)
            elif action == "plan":
                return self._execute_plan(state)
            elif action == "execute":
                return self._execute_task(state, task_id)
            else:
                logger.warning(f"Unknown action: {action}, defaulting to plan")
                return self._execute_plan(state)
                
        except Exception as e:
            logger.error(f"Error executing supervisor action: {e}")
            return {
                "success": False,
                "result": f"Error: {str(e)}",
                "intermediate_steps": [],
                "action": action
            }
    
    def _execute_finalize(self, state: AgentState) -> Dict[str, Any]:
        """Execute finalization action."""
        logger.info("🎯 FINALIZE: Synthesizing final results")
        
        # Get completed tasks
        completed_tasks = state.get("completed_tasks", [])
        todo_list = state.get("todo_list", [])
        
        # Count task statuses
        pending_tasks = [t for t in todo_list if t.get("status") == "pending"]
        completed_count = len(completed_tasks)
        failed_tasks = [t for t in todo_list if t.get("status") == "failed"]
        
        # Create final result
        final_result = f"""## Task Execution Summary

**Completed Tasks**: {completed_count}
**Failed Tasks**: {len(failed_tasks)}
**Pending Tasks**: {len(pending_tasks)}

### Completed Work:
"""
        
        for task in completed_tasks:
            final_result += f"- {task.get('task', 'Unknown task')}\n"
            if task.get('result'):
                final_result += f"  Result: {task.get('result')[:200]}...\n"
            if task.get('artifacts'):
                final_result += f"  Files: {task.get('artifacts')}\n"
        
        if failed_tasks:
            final_result += f"\n### Failed Tasks:\n"
            for task in failed_tasks:
                final_result += f"- {task.get('task', 'Unknown task')}\n"
        
        final_result += f"\n**All tasks completed successfully.**"
        
        return {
            "success": True,
            "result": final_result,
            "intermediate_steps": [],
            "action": "finalize"
        }
    
    def _execute_plan(self, state: AgentState) -> Dict[str, Any]:
        """Execute planning action using LLM."""
        logger.info("🎯 PLAN: Creating task plan using LLM")
        
        # Format the prompt with current state
        formatted_prompt = format_supervisor_prompt(
            objective=state["objective"],
            current_state=state
        )
        
        # Create input message for planning
        input_message = f"""Current State Analysis:
{formatted_prompt}

Action Required: plan

Please analyze the objective and create a detailed task plan using the update_todo_tool. Break down the objective into specific, actionable tasks with appropriate tool assignments."""
        
        # Execute with LLM and tools
        result = self.agent_executor.invoke({
            "input": input_message
        })
        
        return {
            "success": True,
            "result": result.get("output", ""),
            "intermediate_steps": result.get("intermediate_steps", []),
            "action": "plan"
        }
    
    def _build_task_context(self, state: AgentState, current_task_id: int) -> Dict[str, Any]:
        """Build context dictionary for task execution"""
        from src.core.file_system import VirtualFileSystem
        
        fs = VirtualFileSystem()
        
        # Get completed tasks (only those before current task)
        all_tasks = state.get('todo_list', [])
        completed_tasks = []
        
        for task in all_tasks:
            task_id = task.get('id', 999)
            task_status = task.get('status', '')
            
            # Only include completed tasks with lower IDs
            if task_status == 'completed' and task_id < current_task_id:
                completed_tasks.append({
                    'id': task_id,
                    'task': task.get('task', ''),
                    'artifacts': task.get('artifacts', [])  # You may need to track this
                })
        
        return {
            'completed_tasks': completed_tasks,
            'available_files': fs.list_files(),
            'objective': state.get('objective', '')
        }
    
    def _execute_task(self, state: AgentState, task_id: Optional[int]) -> Dict[str, Any]:
        """Execute a specific task using LLM."""
        logger.info(f"🎯 EXECUTE: Running task {task_id}")
        
        # Find the task to execute
        todo_list = state.get("todo_list", [])
        task_to_execute = None
        
        if task_id:
            task_to_execute = next((t for t in todo_list if t.get("id") == task_id), None)
        
        if not task_to_execute:
            # Find first pending task
            task_to_execute = next((t for t in todo_list if t.get("status") == "pending"), None)
        
        if not task_to_execute:
            return {
                "success": False,
                "result": "No pending tasks found to execute",
                "intermediate_steps": [],
                "action": "execute"
            }
        
        # Build context from completed tasks
        context = self._build_task_context(state, task_to_execute.get('id'))
        
        # Format the prompt with current state
        formatted_prompt = format_supervisor_prompt(
            objective=state["objective"],
            current_state=state
        )
        
        # Create input message for task execution
        input_message = f"""Current State Analysis:
{formatted_prompt}

Action Required: execute
Task ID: {task_to_execute.get('id')}

Context for this task:
- Previous tasks: {len(context.get('previous_tasks', []))} completed
- Available files: {context.get('available_files', [])}
- Instructions: {context.get('instructions', '')}

Please execute the specified task using the task_tool with the provided context to help the subagent build upon previous work."""
        
        # Execute with LLM and tools
        result = self.agent_executor.invoke({
            "input": input_message
        })
        
        return {
            "success": True,
            "result": result.get("output", ""),
            "intermediate_steps": result.get("intermediate_steps", []),
            "action": "execute"
        }


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node function for LangGraph.
    
    This is the main entry point for the supervisor in the LangGraph workflow.
    It analyzes the current state, makes decisions, and executes actions.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated agent state
    """
    # DEBUG: Log state at entry
    logger.info(f"🔍 SUPERVISOR ENTRY DEBUG:")
    logger.info(f"   State at entry: todo_list={len(state.get('todo_list', []))} tasks, iteration={state.get('iteration_count', 0)}")
    logger.info(f"   TODO list content: {[t.get('task', 'NO_TASK')[:50] for t in state.get('todo_list', [])]}")
    logger.info(f"   Completed tasks: {len(state.get('completed_tasks', []))}")
    logger.info(f"   Current task: {state.get('current_task')}")
    logger.info(f"   Final result: {state.get('final_result')}")
    
    logger.info(f"Supervisor node called with iteration {state['iteration_count']}")
    
    try:
        # Increment iteration count
        state["iteration_count"] += 1
        logger.info(f"Starting iteration {state['iteration_count']}")
        
        # Check for maximum iterations
        if state["iteration_count"] > MAX_ITERATIONS:
            logger.warning(f"Maximum iterations ({MAX_ITERATIONS}) reached, finalizing")
            state["final_result"] = f"Maximum iterations reached. Completed {len(state['completed_tasks'])} tasks."
            return state
        
        # Initialize supervisor agent if not already done
        if not hasattr(supervisor_node, '_supervisor_agent'):
            from langchain_openai import ChatOpenAI
            import os
            
            # Get OpenAI API key
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Initialize LLM
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                api_key=openai_api_key
            )
            
            # Get supervisor tools
            supervisor_tools = get_supervisor_tools()
            
            # Create supervisor agent
            supervisor_node._supervisor_agent = SupervisorAgent(llm, supervisor_tools)
            logger.info("Supervisor agent initialized")
        
        supervisor_agent = supervisor_node._supervisor_agent
        
        # DEBUG: Log state before decision
        logger.info(f"🔍 PRE-DECISION DEBUG:")
        logger.info(f"   About to make decision with: {len(state.get('todo_list', []))} tasks")
        logger.info(f"   TODO status breakdown: pending={len([t for t in state.get('todo_list', []) if t.get('status') == 'pending'])}, completed={len([t for t in state.get('todo_list', []) if t.get('status') == 'completed'])}")
        logger.info(f"   Current iteration: {state.get('iteration_count', 0)}")
        
        # Decide next action
        decision = supervisor_agent.decide_next_action(state)
        logger.info(f"🔍 DECISION DEBUG:")
        logger.info(f"   Decision made: {decision}")
        logger.info(f"   Action: {decision.get('action')}")
        logger.info(f"   Reasoning: {decision.get('reasoning')}")
        logger.info(f"   Next task ID: {decision.get('next_task_id')}")
        
        # Execute the action
        execution_result = supervisor_agent.execute_action(
            state=state,
            action=decision["action"],
            task_id=decision.get("next_task_id")
        )
        
        # Update state based on execution result
        if execution_result["success"]:
            # Add the execution result to messages
            from langchain.schema import AIMessage
            state["messages"].append(AIMessage(content=execution_result["result"]))
            
            # Handle different actions
            if decision["action"] == "plan":
                logger.info("Planning phase completed")
                # State will be updated by the tools (update_todo_tool)
                
            elif decision["action"] == "execute":
                logger.info(f"Execution phase completed for task {decision.get('next_task_id')}")
                # State will be updated by the tools (task_tool)
                
            elif decision["action"] == "finalize":
                logger.info("Finalization phase completed")
                # Set final result
                if not state["final_result"]:
                    state["final_result"] = execution_result["result"]
        else:
            logger.error(f"Supervisor execution failed: {execution_result['result']}")
            # Add error message
            from langchain.schema import AIMessage
            state["messages"].append(AIMessage(content=f"Error: {execution_result['result']}"))
        
        # Update state with latest TODO list from todo_manager
        from src.core.tools.supervisor_tools import todo_manager
        state["todo_list"] = todo_manager.get_all_tasks()
        
        # Update completed_tasks from TODO list
        completed_tasks = [task for task in state["todo_list"] if task.get("status") == "completed"]
        state["completed_tasks"] = completed_tasks
        
        # DEBUG: Log state after execution
        logger.info(f"🔍 POST-EXECUTION DEBUG:")
        logger.info(f"   TODO list after execution: {len(state.get('todo_list', []))} tasks")
        logger.info(f"   Completed tasks: {len(state.get('completed_tasks', []))}")
        logger.info(f"   TODO list content: {[t.get('task', 'NO_TASK')[:50] for t in state.get('todo_list', [])]}")
        logger.info(f"   TODO status breakdown: pending={len([t for t in state.get('todo_list', []) if t.get('status') == 'pending'])}, completed={len([t for t in state.get('todo_list', []) if t.get('status') == 'completed'])}")
        
        # Check if we should continue or finalize
        pending_tasks = [task for task in state["todo_list"] if task.get("status") == TASK_STATUS_PENDING]
        
        if decision["action"] == "finalize" or not pending_tasks:
            logger.info("Supervisor node completed - finalizing")
            if not state["final_result"]:
                state["final_result"] = "All tasks completed successfully."
        else:
            logger.info(f"Supervisor node completed - {len(pending_tasks)} tasks remaining")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in supervisor_node: {e}")
        # Add error to messages
        from langchain.schema import AIMessage
        state["messages"].append(AIMessage(content=f"Supervisor error: {str(e)}"))
        
        # Set final result to indicate error
        state["final_result"] = f"Supervisor error: {str(e)}"
        return state


def create_supervisor_agent(llm: ChatOpenAI) -> SupervisorAgent:
    """
    Factory function to create a SupervisorAgent with default tools.
    
    Args:
        llm: Language model for the supervisor
        
    Returns:
        Configured SupervisorAgent instance
    """
    supervisor_tools = get_supervisor_tools()
    return SupervisorAgent(llm, supervisor_tools)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def analyze_state_complexity(state: AgentState) -> str:
    """
    Analyze the complexity of the current state.
    
    Args:
        state: Current agent state
        
    Returns:
        Complexity level string
    """
    todo_count = len(state["todo_list"])
    completed_count = len(state["completed_tasks"])
    iteration_count = state["iteration_count"]
    
    if todo_count == 0 and completed_count == 0:
        return "empty"
    elif todo_count <= 2 and iteration_count <= 3:
        return "simple"
    elif todo_count <= 5 and iteration_count <= 10:
        return "moderate"
    else:
        return "complex"


def get_next_pending_task(state: AgentState) -> Optional[Dict[str, Any]]:
    """
    Get the next pending task from the TODO list.
    
    Args:
        state: Current agent state
        
    Returns:
        Next pending task or None
    """
    pending_tasks = [task for task in state["todo_list"] if task.get("status") == TASK_STATUS_PENDING]
    return pending_tasks[0] if pending_tasks else None


def is_completion_ready(state: AgentState) -> bool:
    """
    Check if the system is ready for completion.
    
    Args:
        state: Current agent state
        
    Returns:
        True if ready for completion
    """
    pending_tasks = [task for task in state["todo_list"] if task.get("status") == TASK_STATUS_PENDING]
    return len(pending_tasks) == 0 and state["iteration_count"] > 0

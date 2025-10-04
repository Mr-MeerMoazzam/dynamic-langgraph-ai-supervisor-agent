"""
Agent execution endpoints for the Supervisor Agent API.

This module provides endpoints for executing the Supervisor Agent system,
including task execution, state management, and agent coordination.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime

from src.api.dependencies import get_settings, get_openai_api_key
from src.api.models.requests import AgentExecutionRequest, TaskExecutionRequest
from src.api.models.responses import AgentExecutionResponse, TaskExecutionResponse, AgentStateResponse
from src.core.state import create_initial_state, AgentState
from src.core.agents.supervisor import supervisor_node
from src.core.agents.task_executor import execute_task_node
from src.core.agents.subagent import SubagentExecutor
from src.core.tools.supervisor_tools import get_supervisor_tools

logger = logging.getLogger(__name__)
router = APIRouter()

# Global state storage (in production, use a proper database)
agent_states: Dict[str, AgentState] = {}

@router.post("/execute", response_model=AgentExecutionResponse)
async def execute_agent(request: AgentExecutionRequest) -> AgentExecutionResponse:
    """Execute the Supervisor Agent with a given objective."""
    try:
        # Create initial state
        state = create_initial_state(request.objective)
        state["session_id"] = request.session_id or f"session_{datetime.now().isoformat()}"
        
        # Store state
        agent_states[state["session_id"]] = state
        
        # Execute supervisor node
        updated_state = supervisor_node(state)
        
        # Update stored state
        agent_states[state["session_id"]] = updated_state
        
        # Create enhanced response with detailed information
        todo_list = updated_state.get("todo_list", [])
        completed_tasks = updated_state.get("completed_tasks", [])
        
        # Create detailed summary
        summary = {
            "total_tasks": len(todo_list),
            "completed_tasks": len([t for t in todo_list if t.get("status") == "completed"]),
            "failed_tasks": len([t for t in todo_list if t.get("status") == "failed"]),
            "pending_tasks": len([t for t in todo_list if t.get("status") == "pending"]),
            "artifacts_created": []
        }
        
        # Collect all artifacts from completed tasks
        for task in completed_tasks:
            if isinstance(task, dict) and "artifacts" in task:
                summary["artifacts_created"].extend(task["artifacts"])
        
        # Create enhanced message
        if summary["completed_tasks"] > 0:
            message = f"Agent execution completed successfully. {summary['completed_tasks']} tasks completed, {summary['failed_tasks']} failed."
        else:
            message = "Agent execution completed with no tasks completed."
        
        return AgentExecutionResponse(
            session_id=state["session_id"],
            success=True,
            message=message,
            state=updated_state,
            execution_time=0.0,  # TODO: Add timing
            summary=summary
        )
    except Exception as e:
        logger.error(f"Error executing agent: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")

@router.post("/task/execute", response_model=TaskExecutionResponse)
async def execute_task(request: TaskExecutionRequest) -> TaskExecutionResponse:
    """Execute a specific task using the task executor."""
    try:
        # Get or create state
        if request.session_id and request.session_id in agent_states:
            state = agent_states[request.session_id]
        else:
            state = create_initial_state(request.objective or "Task execution")
            state["session_id"] = request.session_id or f"task_{datetime.now().isoformat()}"
        
        # Set current task
        state["current_task"] = {
            "id": request.task_id,
            "description": request.task_description,
            "assigned_tools": request.assigned_tools,
            "status": "pending"
        }
        
        # Execute task
        updated_state = execute_task_node(state)
        
        # Update stored state
        agent_states[state["session_id"]] = updated_state
        
        # Get execution result
        completed_tasks = updated_state.get("completed_tasks", [])
        task_result = None
        for task in completed_tasks:
            if task.get("id") == request.task_id:
                task_result = task
                break
        
        return TaskExecutionResponse(
            session_id=state["session_id"],
            task_id=request.task_id,
            success=task_result is not None and task_result.get("status") == "completed",
            result=task_result.get("result", "") if task_result else "",
            artifacts=task_result.get("artifacts", []) if task_result else [],
            execution_time=0.0  # TODO: Add timing
        )
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing task: {str(e)}")

@router.get("/state/{session_id}", response_model=AgentStateResponse)
async def get_agent_state(session_id: str) -> AgentStateResponse:
    """Get the current state of an agent session."""
    try:
        if session_id not in agent_states:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        state = agent_states[session_id]
        
        return AgentStateResponse(
            session_id=session_id,
            state=state,
            last_updated=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent state: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting agent state: {str(e)}")

@router.put("/state/{session_id}")
async def update_agent_state(session_id: str, state: AgentState) -> Dict[str, Any]:
    """Update the state of an agent session."""
    try:
        if session_id not in agent_states:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        agent_states[session_id] = state
        
        return {
            "success": True,
            "message": f"State updated for session '{session_id}'",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent state: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating agent state: {str(e)}")

@router.delete("/state/{session_id}")
async def delete_agent_state(session_id: str) -> Dict[str, Any]:
    """Delete an agent session and its state."""
    try:
        if session_id not in agent_states:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        del agent_states[session_id]
        
        return {
            "success": True,
            "message": f"Session '{session_id}' deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent state: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting agent state: {str(e)}")

@router.get("/sessions")
async def list_agent_sessions() -> Dict[str, Any]:
    """List all active agent sessions."""
    try:
        sessions = []
        for session_id, state in agent_states.items():
            sessions.append({
                "session_id": session_id,
                "objective": state.get("objective", ""),
                "iteration_count": state.get("iteration_count", 0),
                "todo_tasks": len(state.get("todo_list", [])),
                "completed_tasks": len(state.get("completed_tasks", [])),
                "status": "completed" if state.get("final_result") else "running"
            })
        
        return {
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
    except Exception as e:
        logger.error(f"Error listing agent sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing agent sessions: {str(e)}")

@router.post("/subagent/execute")
async def execute_subagent(
    task_description: str,
    assigned_tools: List[str],
    context: Dict[str, Any],
    success_criteria: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a subagent directly for a specific task."""
    try:
        # Get OpenAI API key
        openai_api_key = get_openai_api_key()
        
        # Create subagent executor
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=openai_api_key
        )
        
        supervisor_tools = get_supervisor_tools()
        executor = SubagentExecutor(llm, supervisor_tools)
        
        # Execute subagent
        result = executor.run_subagent(
            task_description=task_description,
            assigned_tools=assigned_tools,
            context=context,
            success_criteria=success_criteria,
            max_iterations=15
        )
        
        return {
            "success": result.get("success", False),
            "result": result.get("result", ""),
            "artifacts": result.get("artifacts", []),
            "iterations_used": result.get("iterations_used", 0),
            "execution_time": result.get("execution_time", 0.0)
        }
    except Exception as e:
        logger.error(f"Error executing subagent: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing subagent: {str(e)}")

@router.get("/session/{session_id}/details")
async def get_session_details(session_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific session."""
    try:
        if session_id not in agent_states:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = agent_states[session_id]
        todo_list = state.get("todo_list", [])
        completed_tasks = state.get("completed_tasks", [])
        
        # Create detailed breakdown
        task_breakdown = {
            "total_tasks": len(todo_list),
            "completed_tasks": len([t for t in todo_list if t.get("status") == "completed"]),
            "failed_tasks": len([t for t in todo_list if t.get("status") == "failed"]),
            "pending_tasks": len([t for t in todo_list if t.get("status") == "pending"])
        }
        
        # Collect all artifacts
        all_artifacts = []
        for task in completed_tasks:
            if isinstance(task, dict) and "artifacts" in task:
                all_artifacts.extend(task["artifacts"])
        
        return {
            "session_id": session_id,
            "objective": state.get("objective", ""),
            "iteration_count": state.get("iteration_count", 0),
            "final_result": state.get("final_result", ""),
            "task_breakdown": task_breakdown,
            "todo_list": todo_list,
            "completed_tasks": completed_tasks,
            "artifacts_created": all_artifacts,
            "current_task": state.get("current_task"),
            "messages": state.get("messages", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting session details: {str(e)}")

"""
Request models for the Supervisor Agent API.

This module contains Pydantic models for API request bodies.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class AgentExecutionRequest(BaseModel):
    """Request model for agent execution."""
    objective: str = Field(..., description="The objective for the agent to achieve")
    session_id: Optional[str] = Field(None, description="Optional session ID for state persistence")
    max_iterations: Optional[int] = Field(15, description="Maximum number of iterations")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

class TaskExecutionRequest(BaseModel):
    """Request model for task execution."""
    task_id: int = Field(..., description="ID of the task to execute")
    task_description: str = Field(..., description="Description of the task")
    assigned_tools: List[str] = Field(..., description="Tools assigned to the task")
    session_id: Optional[str] = Field(None, description="Session ID for state persistence")
    objective: Optional[str] = Field(None, description="Overall objective context")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task context")

class FileWriteRequest(BaseModel):
    """Request model for writing files."""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    overwrite: bool = Field(False, description="Whether to overwrite existing file")

class FileEditRequest(BaseModel):
    """Request model for editing files."""
    edits: Union[str, List[Dict[str, str]]] = Field(..., description="Edits to apply to the file")
    edit_type: str = Field("replace", description="Type of edit: 'replace' or 'find_replace'")

class SubagentExecutionRequest(BaseModel):
    """Request model for direct subagent execution."""
    task_description: str = Field(..., description="Description of the task")
    assigned_tools: List[str] = Field(..., description="Tools assigned to the task")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context")
    success_criteria: str = Field(..., description="Success criteria for the task")
    max_iterations: int = Field(15, description="Maximum iterations for the subagent")

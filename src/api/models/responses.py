"""
Response models for the Supervisor Agent API.

This module contains Pydantic models for API response bodies.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from src.core.state import AgentState

class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    session_id: str = Field(..., description="Session ID")
    success: bool = Field(..., description="Whether execution was successful")
    message: str = Field(..., description="Execution message")
    state: AgentState = Field(..., description="Updated agent state")
    execution_time: float = Field(..., description="Execution time in seconds")
    summary: Optional[Dict[str, Any]] = Field(None, description="Execution summary with task counts and artifacts")

class TaskExecutionResponse(BaseModel):
    """Response model for task execution."""
    session_id: str = Field(..., description="Session ID")
    task_id: int = Field(..., description="Task ID")
    success: bool = Field(..., description="Whether task execution was successful")
    result: str = Field(..., description="Task execution result")
    artifacts: List[str] = Field(default_factory=list, description="Files created during execution")
    execution_time: float = Field(..., description="Execution time in seconds")

class AgentStateResponse(BaseModel):
    """Response model for agent state."""
    session_id: str = Field(..., description="Session ID")
    state: AgentState = Field(..., description="Current agent state")
    last_updated: str = Field(..., description="Last update timestamp")

class FileResponse(BaseModel):
    """Response model for file operations."""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    size: int = Field(..., description="File size in bytes")
    exists: bool = Field(..., description="Whether file exists")

class FileListResponse(BaseModel):
    """Response model for file listing."""
    files: List[Dict[str, Any]] = Field(..., description="List of files with details")
    total_files: int = Field(..., description="Total number of files")
    total_size: int = Field(..., description="Total size of all files in bytes")

class FileOperationResponse(BaseModel):
    """Response model for file operations."""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation message")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")

class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    components: Optional[Dict[str, Any]] = Field(None, description="Component health details")

class SubagentExecutionResponse(BaseModel):
    """Response model for subagent execution."""
    success: bool = Field(..., description="Whether execution was successful")
    result: str = Field(..., description="Execution result")
    artifacts: List[str] = Field(default_factory=list, description="Files created")
    iterations_used: int = Field(..., description="Number of iterations used")
    execution_time: float = Field(..., description="Execution time in seconds")

class SessionListResponse(BaseModel):
    """Response model for session listing."""
    sessions: List[Dict[str, Any]] = Field(..., description="List of active sessions")
    total_sessions: int = Field(..., description="Total number of sessions")

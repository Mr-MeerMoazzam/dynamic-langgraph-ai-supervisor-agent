"""
Tests for the Task Executor functionality.

This module contains comprehensive tests for the execute_task_node function
and related task execution utilities, covering successful execution, error
handling, artifact tracking, and context passing.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agents.task_executor import (
    execute_task_node, _prepare_task_context, _define_success_criteria,
    _execute_task_with_tool, _update_state_with_results, _get_existing_artifacts,
    validate_task_execution, get_task_execution_summary, create_task_execution_context,
    format_task_execution_result
)
from src.state import AgentState, create_initial_state, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED
from src.tools.supervisor_tools import task_tool

# Load environment variables
load_dotenv()


class TestTaskExecutorCore:
    """Test cases for core task execution functionality."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Create sample state with current task
        self.sample_state = create_initial_state("Test objective")
        self.sample_state["current_task"] = {
            "id": 1,
            "description": "Test task",
            "assigned_tools": ["execute_code_tool"],
            "status": TASK_STATUS_PENDING
        }
        self.sample_state["todo_list"] = [
            {"id": 1, "description": "Test task", "status": TASK_STATUS_PENDING}
        ]
    
    def test_prepare_task_context(self):
        """Test context preparation for task execution."""
        context = _prepare_task_context(self.sample_state)
        
        assert "objective" in context
        assert "iteration_count" in context
        assert "completed_tasks_count" in context
        assert "pending_tasks_count" in context
        assert context["objective"] == "Test objective"
        assert context["completed_tasks_count"] == 0
        assert context["pending_tasks_count"] == 1
    
    def test_prepare_task_context_with_completed_tasks(self):
        """Test context preparation with completed tasks."""
        # Add completed tasks
        self.sample_state["completed_tasks"] = [
            {
                "id": 0,
                "task": "Previous task",
                "result": "Previous result",
                "artifacts": ["file1.txt", "file2.txt"],
                "status": TASK_STATUS_COMPLETED
            }
        ]
        
        context = _prepare_task_context(self.sample_state)
        
        assert context["completed_tasks_count"] == 1
        assert "recent_completed_tasks" in context
        assert len(context["recent_completed_tasks"]) == 1
        assert context["recent_completed_tasks"][0]["description"] == "Previous task"
    
    def test_define_success_criteria(self):
        """Test success criteria definition."""
        current_task = {
            "description": "Calculate fibonacci(10)",
            "assigned_tools": ["execute_code_tool", "write_file_tool"]
        }
        
        success_criteria = _define_success_criteria(current_task, self.sample_state)
        
        assert "Calculate fibonacci(10)" in success_criteria
        assert "execution results" in success_criteria
        assert "save any important results to files" in success_criteria
        assert "completed successfully" in success_criteria
    
    def test_define_success_criteria_with_search_tool(self):
        """Test success criteria with search tool."""
        current_task = {
            "description": "Research AI agents",
            "assigned_tools": ["search_internet_tool"]
        }
        
        success_criteria = _define_success_criteria(current_task, self.sample_state)
        
        assert "Research AI agents" in success_criteria
        assert "relevant information found" in success_criteria
    
    def test_get_existing_artifacts(self):
        """Test getting existing artifacts from completed tasks."""
        # Add completed tasks with artifacts
        self.sample_state["completed_tasks"] = [
            {
                "id": 1,
                "task": "Task 1",
                "artifacts": ["file1.txt", "file2.txt"],
                "status": TASK_STATUS_COMPLETED
            },
            {
                "id": 2,
                "task": "Task 2", 
                "artifacts": ["file3.txt"],
                "status": TASK_STATUS_COMPLETED
            }
        ]
        
        artifacts = _get_existing_artifacts(self.sample_state)
        
        assert len(artifacts) == 3
        assert "file1.txt" in artifacts
        assert "file2.txt" in artifacts
        assert "file3.txt" in artifacts
    
    def test_validate_task_execution_valid(self):
        """Test task execution validation with valid task."""
        assert validate_task_execution(self.sample_state) is True
    
    def test_validate_task_execution_no_current_task(self):
        """Test task execution validation with no current task."""
        state_no_task = create_initial_state("Test")
        assert validate_task_execution(state_no_task) is False
    
    def test_validate_task_execution_missing_fields(self):
        """Test task execution validation with missing required fields."""
        invalid_state = create_initial_state("Test")
        invalid_state["current_task"] = {"id": 1}  # Missing description and tools
        
        assert validate_task_execution(invalid_state) is False
    
    def test_validate_task_execution_no_tools(self):
        """Test task execution validation with no assigned tools."""
        state_no_tools = create_initial_state("Test")
        state_no_tools["current_task"] = {
            "id": 1,
            "description": "Test task",
            "assigned_tools": []  # No tools
        }
        
        assert validate_task_execution(state_no_tools) is False


class TestTaskExecutionStateUpdates:
    """Test cases for state updates during task execution."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        self.sample_state = create_initial_state("Test objective")
        self.sample_state["current_task"] = {
            "id": 1,
            "description": "Test task",
            "assigned_tools": ["execute_code_tool"],
            "status": TASK_STATUS_PENDING
        }
        self.sample_state["todo_list"] = [
            {"id": 1, "description": "Test task", "status": TASK_STATUS_PENDING}
        ]
    
    def test_update_state_with_successful_result(self):
        """Test state update with successful task execution."""
        execution_result = {
            "success": True,
            "result": "Task completed successfully",
            "artifacts": ["result.txt", "data.json"],
            "details": "All operations completed"
        }
        
        updated_state = _update_state_with_results(
            state=self.sample_state,
            task_id=1,
            task_description="Test task",
            execution_result=execution_result
        )
        
        # Check completed tasks
        assert len(updated_state["completed_tasks"]) == 1
        completed_task = updated_state["completed_tasks"][0]
        assert completed_task["id"] == 1
        assert completed_task["task"] == "Test task"
        assert completed_task["result"] == "Task completed successfully"
        assert completed_task["artifacts"] == ["result.txt", "data.json"]
        assert completed_task["status"] == TASK_STATUS_COMPLETED
        
        # Check TODO list
        assert len(updated_state["todo_list"]) == 0
        
        # Check current task
        assert updated_state["current_task"] is None
        
        # Check messages
        assert len(updated_state["messages"]) > 0
        last_message = updated_state["messages"][-1]
        assert "completed successfully" in last_message.content
    
    def test_update_state_with_failed_result(self):
        """Test state update with failed task execution."""
        execution_result = {
            "success": False,
            "result": "Task failed due to error",
            "artifacts": [],
            "details": "Error: Invalid input"
        }
        
        updated_state = _update_state_with_results(
            state=self.sample_state,
            task_id=1,
            task_description="Test task",
            execution_result=execution_result
        )
        
        # Check completed tasks
        assert len(updated_state["completed_tasks"]) == 1
        completed_task = updated_state["completed_tasks"][0]
        assert completed_task["status"] == TASK_STATUS_FAILED
        assert "failed" in completed_task["result"]
        
        # Check messages
        last_message = updated_state["messages"][-1]
        assert "failed" in last_message.content
    
    def test_get_task_execution_summary(self):
        """Test task execution summary generation."""
        # Add some completed and pending tasks
        self.sample_state["completed_tasks"] = [
            {
                "id": 1,
                "task": "Task 1",
                "status": TASK_STATUS_COMPLETED,
                "artifacts": ["file1.txt"]
            },
            {
                "id": 2,
                "task": "Task 2",
                "status": TASK_STATUS_FAILED,
                "artifacts": []
            }
        ]
        self.sample_state["todo_list"] = [
            {"id": 3, "description": "Task 3", "status": TASK_STATUS_PENDING}
        ]
        
        summary = get_task_execution_summary(self.sample_state)
        
        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 2
        assert summary["successful_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["pending_tasks"] == 1
        assert summary["total_artifacts"] == 1
        assert summary["completion_rate"] == 2/3 * 100
        assert summary["success_rate"] == 1/2 * 100


class TestTaskExecutorUtilities:
    """Test cases for task executor utility functions."""
    
    def test_create_task_execution_context(self):
        """Test creating standardized context for task execution."""
        objective = "Test objective"
        completed_tasks = [
            {
                "task": "Task 1",
                "result": "Result 1"
            },
            {
                "task": "Task 2", 
                "result": "Result 2"
            }
        ]
        current_iteration = 5
        
        context = create_task_execution_context(objective, completed_tasks, current_iteration)
        
        assert context["objective"] == "Test objective"
        assert context["iteration"] == 5
        assert context["completed_tasks_count"] == 2
        assert len(context["recent_findings"]) == 2
        assert context["recent_findings"][0]["task"] == "Task 1"
        assert context["recent_findings"][0]["result"] == "Result 1"
    
    def test_format_task_execution_result_success(self):
        """Test formatting successful task execution result."""
        execution_result = {
            "success": True,
            "result": "Task completed successfully with detailed results",
            "artifacts": ["file1.txt", "file2.txt"],
            "details": "All operations completed without errors"
        }
        
        formatted = format_task_execution_result(1, "Test task", execution_result)
        
        assert "Task 1: ✅ SUCCESS" in formatted
        assert "Test task" in formatted
        assert "Task completed successfully" in formatted
        assert "2 files created" in formatted
        assert "All operations completed" in formatted
    
    def test_format_task_execution_result_failure(self):
        """Test formatting failed task execution result."""
        execution_result = {
            "success": False,
            "result": "Task failed due to error",
            "artifacts": [],
            "details": "Error: Invalid input provided"
        }
        
        formatted = format_task_execution_result(1, "Test task", execution_result)
        
        assert "Task 1: ❌ FAILED" in formatted
        assert "Test task" in formatted
        assert "Task failed due to error" in formatted
        assert "Error: Invalid input" in formatted


class TestTaskExecutorIntegration:
    """Integration tests for task execution with LLM and tools."""
    
    @pytest.mark.integration
    def test_execute_simple_task(self):
        """Test executing a simple task end-to-end."""
        # This test requires actual LLM and API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        # Create state with current task
        state = create_initial_state("Calculate the sum of squares from 1 to 10")
        state["current_task"] = {
            "id": 1,
            "description": "Calculate the sum of squares from 1 to 10",
            "assigned_tools": ["execute_code_tool"],
            "status": TASK_STATUS_PENDING
        }
        state["todo_list"] = [
            {"id": 1, "description": "Calculate the sum of squares from 1 to 10", "status": TASK_STATUS_PENDING}
        ]
        
        # Execute the task
        result_state = execute_task_node(state)
        
        # Verify state updates
        assert len(result_state["completed_tasks"]) == 1
        completed_task = result_state["completed_tasks"][0]
        assert completed_task["id"] == 1
        assert completed_task["status"] in [TASK_STATUS_COMPLETED, TASK_STATUS_FAILED]
        
        # Verify TODO list is updated
        assert len(result_state["todo_list"]) == 0
        
        # Verify current task is cleared
        assert result_state["current_task"] is None
        
        # Verify messages are added
        assert len(result_state["messages"]) > 0
    
    @pytest.mark.integration
    def test_task_execution_artifacts(self):
        """Test that artifacts are properly tracked during task execution."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        # Create state with file creation task
        state = create_initial_state("Create a text file with hello world")
        state["current_task"] = {
            "id": 1,
            "description": "Create a text file with hello world",
            "assigned_tools": ["write_file_tool"],
            "status": TASK_STATUS_PENDING
        }
        state["todo_list"] = [
            {"id": 1, "description": "Create a text file with hello world", "status": TASK_STATUS_PENDING}
        ]
        
        # Execute the task
        result_state = execute_task_node(state)
        
        # Verify artifacts are tracked
        if result_state["completed_tasks"]:
            completed_task = result_state["completed_tasks"][0]
            assert "artifacts" in completed_task
            # Artifacts should be a list
            assert isinstance(completed_task["artifacts"], list)
    
    @pytest.mark.integration
    def test_failed_task_handling(self):
        """Test graceful handling of failed tasks."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        # Create state with a task that might fail
        state = create_initial_state("Execute invalid Python code")
        state["current_task"] = {
            "id": 1,
            "description": "Execute invalid Python code that will cause an error",
            "assigned_tools": ["execute_code_tool"],
            "status": TASK_STATUS_PENDING
        }
        state["todo_list"] = [
            {"id": 1, "description": "Execute invalid Python code that will cause an error", "status": TASK_STATUS_PENDING}
        ]
        
        # Execute the task
        result_state = execute_task_node(state)
        
        # Verify task is marked as failed but system continues
        assert len(result_state["completed_tasks"]) == 1
        completed_task = result_state["completed_tasks"][0]
        assert completed_task["status"] == TASK_STATUS_FAILED
        
        # Verify error message is added
        assert len(result_state["messages"]) > 0
        last_message = result_state["messages"][-1]
        assert "failed" in last_message.content.lower()
    
    @pytest.mark.integration
    def test_context_passing(self):
        """Test that relevant context is passed to subagent."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        # Create state with previous completed tasks
        state = create_initial_state("Build on previous work")
        state["completed_tasks"] = [
            {
                "id": 0,
                "task": "Previous task",
                "result": "Previous result",
                "artifacts": ["previous_file.txt"],
                "status": TASK_STATUS_COMPLETED
            }
        ]
        state["current_task"] = {
            "id": 1,
            "description": "Use previous results to create new output",
            "assigned_tools": ["read_file_tool", "write_file_tool"],
            "status": TASK_STATUS_PENDING
        }
        state["todo_list"] = [
            {"id": 1, "description": "Use previous results to create new output", "status": TASK_STATUS_PENDING}
        ]
        
        # Execute the task
        result_state = execute_task_node(state)
        
        # Verify task execution (may succeed or fail, but should handle context)
        assert len(result_state["completed_tasks"]) >= 1
        # The important thing is that the system doesn't crash with context


class TestTaskExecutorEdgeCases:
    """Test edge cases for task execution."""
    
    def test_execute_task_node_no_current_task(self):
        """Test execute_task_node with no current task."""
        state = create_initial_state("Test objective")
        # No current_task set
        
        result_state = execute_task_node(state)
        
        # Should handle gracefully
        assert "current_task" not in result_state or result_state["current_task"] is None
        assert len(result_state["messages"]) > 0
        last_message = result_state["messages"][-1]
        assert "No current task" in last_message.content
    
    def test_execute_task_node_malformed_task(self):
        """Test execute_task_node with malformed current task."""
        state = create_initial_state("Test objective")
        state["current_task"] = {
            "id": 1
            # Missing description and assigned_tools
        }
        
        result_state = execute_task_node(state)
        
        # Should handle gracefully
        assert len(result_state["messages"]) > 0
    
    def test_execute_task_node_tool_failure(self):
        """Test execute_task_node when task_tool fails."""
        state = create_initial_state("Test objective")
        state["current_task"] = {
            "id": 1,
            "description": "Test task",
            "assigned_tools": ["execute_code_tool"],
            "status": TASK_STATUS_PENDING
        }
        
        # Mock task_tool to raise exception
        with patch('src.agents.task_executor.task_tool') as mock_task_tool:
            mock_task_tool.invoke.side_effect = Exception("Tool execution failed")
            
            result_state = execute_task_node(state)
            
            # Should handle gracefully
            assert len(result_state["completed_tasks"]) == 1
            completed_task = result_state["completed_tasks"][0]
            assert completed_task["status"] == TASK_STATUS_FAILED
            assert "Tool execution failed" in completed_task["result"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

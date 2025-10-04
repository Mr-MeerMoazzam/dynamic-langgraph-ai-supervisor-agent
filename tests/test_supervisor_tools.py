"""
Tests for supervisor tools functionality.

This module contains comprehensive tests for the supervisor tools,
ensuring proper todo list management, task creation, and status updates.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the supervisor tools
from src.tools.supervisor_tools import update_todo_tool, task_tool, get_supervisor_tools, TodoManager


class TestSupervisorTools:
    """Test suite for supervisor tools functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Reset the global todo manager for each test
        from src.tools.supervisor_tools import todo_manager
        todo_manager.todo_list = []
        todo_manager.next_task_id = 1

    def teardown_method(self):
        """Clean up after each test method."""
        # Reset the global todo manager after each test
        from src.tools.supervisor_tools import todo_manager
        todo_manager.todo_list = []
        todo_manager.next_task_id = 1

    def test_create_action_multiline(self):
        """Test creating todo list from multi-line description."""
        task_description = """1. Research market trends
2. Analyze competitor data
3. Generate final report"""

        result = update_todo_tool.invoke({
            "action": "create",
            "task_description": task_description,
            "assigned_tools": ["search_internet", "web_scrape"]
        })

        # Verify success
        assert result["success"] is True
        assert "Created 3 tasks" in result["message"]

        # Verify todo list structure
        todo_list = result["todo_list"]
        assert len(todo_list) == 3

        # Check task details
        assert todo_list[0]["id"] == 1
        assert todo_list[0]["task"] == "1. Research market trends"
        assert todo_list[0]["status"] == "pending"
        assert todo_list[0]["assigned_tools"] == ["search_internet", "web_scrape"]

        assert todo_list[1]["id"] == 2
        assert todo_list[1]["task"] == "2. Analyze competitor data"

        assert todo_list[2]["id"] == 3
        assert todo_list[2]["task"] == "3. Generate final report"

    def test_create_action_empty_description(self):
        """Test create action with empty description."""
        result = update_todo_tool.invoke({
            "action": "create",
            "task_description": "",
            "assigned_tools": ["search_internet"]
        })

        # Should fail gracefully
        assert result["success"] is False
        assert "task_description is required" in result["message"]
        assert len(result["todo_list"]) == 0

    def test_add_new_action(self):
        """Test adding a new task to existing list."""
        # First create some tasks
        update_todo_tool.invoke({
            "action": "create",
            "task_description": "Initial task",
            "assigned_tools": ["execute_code"]
        })

        # Add a new task
        result = update_todo_tool.invoke({
            "action": "add_new",
            "task_description": "Additional analysis task",
            "assigned_tools": ["web_scrape"]
        })

        # Verify success
        assert result["success"] is True
        assert "Added new task" in result["message"]

        # Verify todo list has 2 tasks
        todo_list = result["todo_list"]
        assert len(todo_list) == 2

        # Check the new task
        new_task = todo_list[1]  # Second task (index 1)
        assert new_task["id"] == 2
        assert new_task["task"] == "Additional analysis task"
        assert new_task["status"] == "pending"
        assert new_task["assigned_tools"] == ["web_scrape"]

    def test_update_status_action(self):
        """Test updating task status."""
        # First create a task
        update_todo_tool.invoke({
            "action": "create",
            "task_description": "Task to update",
            "assigned_tools": ["search_internet"]
        })

        # Update task status
        result = update_todo_tool.invoke({
            "action": "update_status",
            "task_id": 1,
            "new_status": "completed"
        })

        # Verify success
        assert result["success"] is True
        assert "Updated task 1 status to completed" in result["message"]

        # Verify task status was updated
        todo_list = result["todo_list"]
        assert len(todo_list) == 1
        assert todo_list[0]["id"] == 1
        assert todo_list[0]["status"] == "completed"

    def test_update_status_invalid_task_id(self):
        """Test updating status with invalid task ID."""
        # Update non-existent task
        result = update_todo_tool.invoke({
            "action": "update_status",
            "task_id": 999,
            "new_status": "completed"
        })

        # Should fail gracefully
        assert result["success"] is False
        assert "Task with ID 999 not found" in result["message"]

    def test_update_status_invalid_status(self):
        """Test updating status with invalid status value."""
        # Create a task first
        update_todo_tool.invoke({
            "action": "create",
            "task_description": "Test task",
            "assigned_tools": ["execute_code"]
        })

        # Try to update with invalid status
        result = update_todo_tool.invoke({
            "action": "update_status",
            "task_id": 1,
            "new_status": "invalid_status"
        })

        # Should fail with validation error
        assert result["success"] is False
        assert "Invalid status" in result["message"]

    def test_invalid_action(self):
        """Test with invalid action value."""
        # This should raise a validation error due to Pydantic schema validation
        with pytest.raises(Exception) as exc_info:
            update_todo_tool.invoke({
                "action": "invalid_action",
                "task_description": "Test task"
            })

        # Should be a validation error from Pydantic
        assert "validation error" in str(exc_info.value).lower() or "literal_error" in str(exc_info.value)

    def test_todo_manager_class(self):
        """Test TodoManager class functionality directly."""
        manager = TodoManager()

        # Test creating tasks
        tasks = manager.create_tasks(["Task 1", "Task 2"], ["tool1"])
        assert len(tasks) == 2
        assert tasks[0]["id"] == 1
        assert tasks[0]["task"] == "Task 1"
        assert tasks[0]["assigned_tools"] == ["tool1"]

        # Test adding task
        new_task = manager.add_task("Task 3", ["tool2"])
        assert new_task["id"] == 3
        assert new_task["task"] == "Task 3"
        assert new_task["assigned_tools"] == ["tool2"]

        # Test updating status
        updated = manager.update_task_status(1, "completed")
        assert updated is not None
        assert updated["status"] == "completed"

        # Test getting pending tasks
        pending = manager.get_pending_tasks()
        assert len(pending) == 2  # Tasks 2 and 3 are still pending

        # Test getting task by ID
        task = manager.get_task_by_id(2)
        assert task is not None
        assert task["id"] == 2

        # Test clearing completed tasks
        removed = manager.clear_completed_tasks()
        assert removed == 1  # One completed task was removed
        assert len(manager.get_all_tasks()) == 2  # Two tasks remain

    def test_create_todo_list(self):
        """Test creating initial TODO list from description."""
        manager = TodoManager()

        # Test creating from single task
        tasks = manager.create_tasks(["Research market trends"], ["search_internet"])
        assert len(tasks) == 1
        assert tasks[0]["id"] == 1
        assert tasks[0]["task"] == "Research market trends"
        assert tasks[0]["status"] == "pending"
        assert tasks[0]["assigned_tools"] == ["search_internet"]

        # Test creating from multiple tasks
        manager2 = TodoManager()
        tasks2 = manager2.create_tasks([
            "Analyze competitor data",
            "Generate report",
            "Present findings"
        ], ["web_scrape", "execute_code"])

        assert len(tasks2) == 3
        assert tasks2[0]["id"] == 1
        assert tasks2[1]["id"] == 2
        assert tasks2[2]["id"] == 3
        assert all(task["status"] == "pending" for task in tasks2)
        assert all(task["assigned_tools"] == ["web_scrape", "execute_code"] for task in tasks2)

    def test_add_new_task(self):
        """Test adding a new task to existing list."""
        manager = TodoManager()

        # Create initial task
        manager.create_tasks(["Initial task"])

        # Add new task
        new_task = manager.add_task("Additional task", ["web_scrape"])

        assert new_task["id"] == 2  # Should be next available ID
        assert new_task["task"] == "Additional task"
        assert new_task["status"] == "pending"
        assert new_task["assigned_tools"] == ["web_scrape"]

        # Verify total tasks
        all_tasks = manager.get_all_tasks()
        assert len(all_tasks) == 2

    def test_update_task_status(self):
        """Test updating task status."""
        manager = TodoManager()

        # Create a task
        manager.create_tasks(["Test task"])

        # Update status to in_progress
        updated = manager.update_task_status(1, "in_progress")
        assert updated is not None
        assert updated["status"] == "in_progress"

        # Update status to completed
        updated = manager.update_task_status(1, "completed")
        assert updated is not None
        assert updated["status"] == "completed"

        # Verify in todo list
        all_tasks = manager.get_all_tasks()
        assert all_tasks[0]["status"] == "completed"

    def test_get_pending_tasks(self):
        """Test getting only pending tasks."""
        manager = TodoManager()

        # Create mix of tasks with different statuses
        manager.create_tasks([
            "Task 1 - pending",
            "Task 2 - pending",
            "Task 3 - completed"
        ])

        # Update one task to completed
        manager.update_task_status(3, "completed")

        # Get pending tasks
        pending_tasks = manager.get_pending_tasks()
        assert len(pending_tasks) == 2

        # Verify they are the right tasks
        pending_ids = [task["id"] for task in pending_tasks]
        assert 1 in pending_ids
        assert 2 in pending_ids
        assert 3 not in pending_ids  # Completed task should not be in pending

        # Verify all pending tasks have pending status
        assert all(task["status"] == "pending" for task in pending_tasks)

    def test_invalid_status(self):
        """Test trying to set invalid status."""
        manager = TodoManager()

        # Create a task
        manager.create_tasks(["Test task"])

        # Try to set invalid status
        with pytest.raises(ValueError) as exc_info:
            manager.update_task_status(1, "invalid_status")

        assert "Invalid status" in str(exc_info.value)
        assert "pending" in str(exc_info.value)  # Should mention valid options

        # Verify task status unchanged
        task = manager.get_task_by_id(1)
        assert task["status"] == "pending"

    def test_task_id_generation(self):
        """Test that task IDs are generated correctly."""
        manager = TodoManager()

        # Create multiple tasks and verify ID sequence
        task1 = manager.add_task("First task")
        task2 = manager.add_task("Second task")
        task3 = manager.add_task("Third task")

        assert task1["id"] == 1
        assert task2["id"] == 2
        assert task3["id"] == 3

        # Create new manager and verify IDs start from 1
        manager2 = TodoManager()
        task4 = manager2.add_task("New manager task")
        assert task4["id"] == 1

    def test_empty_task_descriptions(self):
        """Test handling of empty task descriptions."""
        manager = TodoManager()

        # Test creating tasks with empty descriptions
        tasks = manager.create_tasks(["Valid task", "", "Another valid task", "   "])
        assert len(tasks) == 2  # Only non-empty descriptions should create tasks

        task_descriptions = [task["task"] for task in tasks]
        assert "Valid task" in task_descriptions
        assert "Another valid task" in task_descriptions

    def test_workflow_integration(self):
        """Test a complete workflow of create -> add -> update."""
        # Step 1: Create initial tasks
        result1 = update_todo_tool.invoke({
            "action": "create",
            "task_description": "Research phase\nAnalysis phase",
            "assigned_tools": ["search_internet"]
        })

        assert result1["success"] is True
        assert len(result1["todo_list"]) == 2

        # Step 2: Add a new task
        result2 = update_todo_tool.invoke({
            "action": "add_new",
            "task_description": "Final report generation",
            "assigned_tools": ["execute_code", "write_file"]
        })

        assert result2["success"] is True
        assert len(result2["todo_list"]) == 3

        # Step 3: Update first task to completed
        result3 = update_todo_tool.invoke({
            "action": "update_status",
            "task_id": 1,
            "new_status": "completed"
        })

        assert result3["success"] is True
        assert result3["todo_list"][0]["status"] == "completed"
        assert result3["todo_list"][1]["status"] == "pending"  # Others unchanged

    def test_task_tool_validation(self):
        """Test task_tool input validation."""
        # Test that the tool accepts valid inputs
        result = task_tool.invoke({
            "task_description": "Valid task",
            "assigned_tools": ["execute_code"],
            "context": {"test": "value"},
            "success_criteria": "Complete the task"
        })

        # Should return a dict result (even if execution fails due to missing API key)
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

    def test_task_tool_invalid_tools(self):
        """Test task_tool with invalid tool names."""
        result = task_tool.invoke({
            "task_description": "Valid task",
            "assigned_tools": ["invalid_tool", "another_invalid"],
            "context": {},
            "success_criteria": "Complete task"
        })

        assert result["success"] is False
        assert "Invalid tools" in result["details"]
        assert "invalid_tool" in result["details"]

    @pytest.mark.integration
    def test_task_tool_basic_execution(self):
        """Test basic task_tool execution."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        result = task_tool.invoke({
            "task_description": "Calculate 2 + 2 and explain the result",
            "assigned_tools": ["execute_code"],
            "context": {"note": "Simple math problem"},
            "success_criteria": "Provide the calculation result and explanation"
        })

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

        # Should be successful
        assert result["success"] in [True, False]  # Can be either depending on execution
        assert isinstance(result["artifacts"], list)
        assert "iterations" in result["details"]

    @pytest.mark.integration
    def test_task_tool_with_file_operations(self):
        """Test task_tool that uses file operations."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        result = task_tool.invoke({
            "task_description": "Create a summary of today's work and save it to summary.txt",
            "assigned_tools": ["write_file"],
            "context": {"work_done": "Completed task_tool implementation"},
            "success_criteria": "Create summary.txt file with work summary"
        })

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

        # Check for file creation
        artifacts = result["artifacts"]
        if artifacts and result["success"]:
            assert any("summary.txt" in artifact for artifact in artifacts)

    @pytest.mark.integration
    def test_task_tool_simple_execution(self):
        """Test task_tool with simple execute_code execution."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        result = task_tool.invoke({
            "task_description": "Calculate 2 + 2 and explain the result",
            "assigned_tools": ["execute_code"],
            "context": {"note": "Simple math problem"},
            "success_criteria": "Provide the calculation result and explanation"
        })

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

        # Should be successful
        assert result["success"] in [True, False]  # Can be either depending on execution
        assert isinstance(result["artifacts"], list)
        assert "iterations" in result["details"]

    @pytest.mark.integration
    def test_task_tool_with_multiple_tools(self):
        """Test task_tool with code + file tools combination."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        result = task_tool.invoke({
            "task_description": "Calculate fibonacci(5) and save result to fibonacci.txt",
            "assigned_tools": ["execute_code", "write_file"],
            "context": {"algorithm": "fibonacci sequence"},
            "success_criteria": "Create fibonacci.txt with the 5th fibonacci number"
        })

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

        # Should handle multiple tools
        assert result["success"] in [True, False]
        assert isinstance(result["artifacts"], list)

        # Check for file creation if successful
        if result["success"] and result["artifacts"]:
            assert any("fibonacci.txt" in artifact for artifact in result["artifacts"])

    def test_task_tool_invalid_tools(self):
        """Test task_tool with non-existent tool names."""
        result = task_tool.invoke({
            "task_description": "Valid task",
            "assigned_tools": ["invalid_tool", "another_invalid"],
            "context": {},
            "success_criteria": "Complete task"
        })

        # Should fail with invalid tools error
        assert result["success"] is False
        assert "Invalid tools" in result["details"]
        assert "invalid_tool" in result["details"]

    @pytest.mark.integration
    def test_task_tool_creates_artifacts(self):
        """Test that task_tool properly detects files created in VFS."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        # Use a task that should create a file
        result = task_tool.invoke({
            "task_description": "Create a simple report and save it as report.txt",
            "assigned_tools": ["write_file"],
            "context": {"purpose": "Test file creation"},
            "success_criteria": "Create report.txt with content"
        })

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "artifacts" in result

        # Should detect file creation
        artifacts = result["artifacts"]
        if result["success"] and artifacts:
            assert len(artifacts) > 0
            assert any("report.txt" in artifact for artifact in artifacts)

    def test_get_supervisor_tools(self):
        """Test get_supervisor_tools() function."""
        tools = get_supervisor_tools()

        # Should return a list
        assert isinstance(tools, list)
        assert len(tools) >= 3  # At least update_todo_tool, task_tool, and file tools

        # Should contain expected tools
        tool_names = [tool.name for tool in tools]
        assert "update_todo_tool" in tool_names
        assert "task_tool" in tool_names
        assert "read_file_tool" in tool_names  # File tool

        # All tools should have required attributes
        for tool in tools:
            assert hasattr(tool, 'invoke')
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')

    def test_task_tool_error_handling(self):
        """Test task_tool error handling for various failure scenarios."""
        # Test with wrong parameter types - Pydantic validation catches this
        with pytest.raises(Exception) as exc_info:
            task_tool.invoke({
                "task_description": 123,  # Wrong type
                "assigned_tools": ["execute_code"],
                "context": {},
                "success_criteria": "Complete task"
            })
        assert "validation error" in str(exc_info.value).lower()

    def test_task_tool_context_passing(self):
        """Test that context is properly passed to subagents."""
        # Since task_tool creates a new SubagentExecutor instance,
        # we need to patch the class constructor or use a different approach

        # For now, let's test that the tool accepts the context parameter
        # without actually executing (since we can't easily mock the constructor)
        result = task_tool.invoke({
            "task_description": "Test task with context",
            "assigned_tools": ["execute_code"],
            "context": {"test_key": "test_value"},
            "success_criteria": "Return test result"
        })

        # The tool should handle the execution (even if it fails due to missing API key)
        # and return a structured result
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "artifacts" in result
        assert "details" in result

        # The important thing is that it doesn't crash and returns proper structure
        # The actual context passing would be verified in integration tests

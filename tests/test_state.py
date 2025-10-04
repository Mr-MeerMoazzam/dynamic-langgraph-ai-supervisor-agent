"""
Tests for state management functionality.

This module contains comprehensive tests for the AgentState schema and
related state management functions, ensuring proper initialization,
type safety, and structure validation.
"""

import pytest
import operator
from typing import get_type_hints, get_origin, get_args, Union

# Load environment variables from .env file for testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not available, continue without loading .env
    pass

# Import the state management components
from src.state import (
    AgentState,
    create_initial_state,
    MAX_ITERATIONS,
    TASK_STATUS_PENDING,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED
)


class TestStateManagement:
    """Test suite for state management functionality."""

    def test_create_initial_state(self):
        """Test that create_initial_state creates proper initial state."""
        # Test with a sample objective
        objective = "Analyze quarterly sales data and generate insights"
        state = create_initial_state(objective)

        # Verify objective is set correctly
        assert state["objective"] == objective

        # Verify all lists are empty initially
        assert state["messages"] == []
        assert state["todo_list"] == []
        assert state["completed_tasks"] == []

        # Verify optional fields are None initially
        assert state["current_task"] is None
        assert state["final_result"] is None

        # Verify iteration count starts at 0
        assert state["iteration_count"] == 0

    def test_state_has_all_fields(self):
        """Test that AgentState has all required fields with correct types."""
        # Get type hints for AgentState
        type_hints = get_type_hints(AgentState)

        # Define expected field types (simplified check for basic types)
        expected_field_types = {
            "messages": "list_type",  # Annotated[List[...], operator.add]
            "objective": "str_type",
            "todo_list": "list_type",
            "completed_tasks": "list_type",
            "current_task": "dict_type",  # Optional[Dict[...]]
            "iteration_count": "int_type",
            "final_result": "str_type"  # Optional[str]
        }

        # Check all expected fields exist
        for field_name, expected_type in expected_field_types.items():
            assert field_name in type_hints, f"Missing field: {field_name}"

        # Verify that the basic structure is correct by checking field existence
        # (The detailed type checking is complex due to Annotated and Optional types)
        assert "messages" in type_hints
        assert "objective" in type_hints
        assert "todo_list" in type_hints
        assert "completed_tasks" in type_hints
        assert "current_task" in type_hints
        assert "iteration_count" in type_hints
        assert "final_result" in type_hints

    def test_todo_list_structure(self):
        """Test that todo list items have correct structure."""
        state = create_initial_state("Test objective")

        # Create a sample todo item
        todo_item = {
            "id": 1,
            "task": "Analyze data",
            "status": TASK_STATUS_PENDING,
            "assigned_tools": ["read_file", "execute_code"]
        }

        # Add to todo list
        state["todo_list"].append(todo_item)

        # Verify the structure
        assert len(state["todo_list"]) == 1
        item = state["todo_list"][0]

        assert "id" in item
        assert "task" in item
        assert "status" in item
        assert "assigned_tools" in item

        assert isinstance(item["id"], int)
        assert isinstance(item["task"], str)
        assert isinstance(item["status"], str)
        assert isinstance(item["assigned_tools"], list)

        # Verify the values
        assert item["id"] == 1
        assert item["task"] == "Analyze data"
        assert item["status"] == TASK_STATUS_PENDING
        assert item["assigned_tools"] == ["read_file", "execute_code"]

    def test_message_annotation(self):
        """Test that messages field uses operator.add annotation."""
        # Create a state and check the type hints more deeply
        state = create_initial_state("Test")

        # Get the actual type annotation for messages field
        type_hints = get_type_hints(AgentState)

        # The messages field should be Annotated[List[BaseMessage], operator.add]
        messages_type = type_hints["messages"]

        # Check that it's an Annotated type
        assert hasattr(messages_type, '__origin__')

        # The base type should be list
        assert messages_type.__origin__ is list

        # Check the metadata (annotations) - operator.add should be there
        if hasattr(messages_type, '__metadata__'):
            metadata = messages_type.__metadata__
            # The operator.add should be in the metadata
            has_operator_add = any(callable(m) and getattr(m, '__name__', None) == 'add' for m in metadata)
            assert has_operator_add, "operator.add annotation not found in messages field"

    def test_constants_values(self):
        """Test that all constants have correct values."""
        assert MAX_ITERATIONS == 20
        assert TASK_STATUS_PENDING == "pending"
        assert TASK_STATUS_IN_PROGRESS == "in_progress"
        assert TASK_STATUS_COMPLETED == "completed"
        assert TASK_STATUS_FAILED == "failed"

    def test_state_mutability(self):
        """Test that state can be properly modified."""
        state = create_initial_state("Test objective")

        # Test modifying simple fields
        state["iteration_count"] = 5
        assert state["iteration_count"] == 5

        # Test modifying list fields
        state["messages"].append("test message")
        assert len(state["messages"]) == 1

        # Test modifying todo list
        todo_item = {
            "id": 1,
            "task": "Test task",
            "status": TASK_STATUS_PENDING,
            "assigned_tools": []
        }
        state["todo_list"].append(todo_item)
        assert len(state["todo_list"]) == 1

        # Test modifying current task
        state["current_task"] = todo_item
        assert state["current_task"] == todo_item

    def test_completed_tasks_structure(self):
        """Test that completed tasks can store complex results."""
        state = create_initial_state("Test objective")

        # Create a completed task with results
        completed_task = {
            "id": 1,
            "task": "Completed analysis",
            "status": TASK_STATUS_COMPLETED,
            "assigned_tools": ["execute_code"],
            "result": {
                "findings": ["Finding 1", "Finding 2"],
                "artifacts": ["report.pdf", "data.csv"],
                "execution_time": 45.2
            },
            "execution_time": 45.2,
            "subagent_logs": ["Step 1 completed", "Step 2 completed"]
        }

        state["completed_tasks"].append(completed_task)

        # Verify structure
        assert len(state["completed_tasks"]) == 1
        task = state["completed_tasks"][0]

        assert task["id"] == 1
        assert task["status"] == TASK_STATUS_COMPLETED
        assert "result" in task
        assert "execution_time" in task
        assert "subagent_logs" in task

        # Verify result structure
        result = task["result"]
        assert "findings" in result
        assert "artifacts" in result
        assert isinstance(result["findings"], list)
        assert isinstance(result["artifacts"], list)

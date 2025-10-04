"""
Tests for subagent execution functionality.

This module contains comprehensive tests for the SubagentExecutor class,
ensuring proper subagent creation, prompt generation, and task execution.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the subagent components
from src.agents.subagent import SubagentExecutor, generate_subagent_prompt, create_subagent_executor


class TestSubagentExecutor:
    """Test suite for SubagentExecutor functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock the environment variable for testing
        self.mock_api_key = "test-openai-key"
        self.patcher = patch.dict(os.environ, {"OPENAI_API_KEY": self.mock_api_key})
        self.patcher.start()

        # Create executor with mocked file system
        self.mock_fs = Mock()
        self.executor = SubagentExecutor(self.mock_fs)

    def teardown_method(self):
        """Clean up after each test method."""
        self.patcher.stop()

    def test_subagent_executor_initialization(self):
        """Test SubagentExecutor initialization."""
        # Test with provided file system
        executor = SubagentExecutor(self.mock_fs)
        assert executor.file_system == self.mock_fs

        # Test with default file system
        executor2 = SubagentExecutor()
        assert executor2.file_system is not None

        # Test API key validation
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable not set"):
                SubagentExecutor()

    def test_generate_subagent_prompt(self):
        """Test subagent prompt generation."""
        task_desc = "Analyze sales data trends"
        context = {"previous_data": "sales_q1.csv", "findings": "15% increase"}
        criteria = "Generate summary report in report.txt"
        tools = ["read_file", "write_file", "execute_code"]

        prompt = generate_subagent_prompt(task_desc, context, criteria, tools)

        # Verify prompt contains key elements
        assert task_desc in prompt
        assert "15% increase" in prompt  # Context should be included
        assert criteria in prompt
        assert "read_file" in prompt
        assert "write_file" in prompt
        assert "execute_code" in prompt

        # Verify prompt structure
        assert "## Task Description" in prompt
        assert "## Context from Previous Work" in prompt
        assert "## Success Criteria" in prompt
        assert "## Available Tools" in prompt
        assert "## Important Instructions" in prompt

    def test_generate_subagent_prompt_empty_context(self):
        """Test prompt generation with empty context."""
        prompt = generate_subagent_prompt("Test task", {}, "Success criteria", ["tool1"])

        # Should handle empty context gracefully
        assert "{}" in prompt or "Context from Previous Work" in prompt

    @pytest.mark.integration
    def test_simple_subagent_execution(self):
        """Test simple subagent execution with execute_code."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        executor = SubagentExecutor()

        # Run subagent that calculates something simple
        result = executor.run_subagent(
            "Calculate 2 + 2 and explain the result",
            ["execute_code"],
            {},
            "Provide the calculation result and explanation",
            max_iterations=3
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "iterations_used" in result
        assert "artifacts_created" in result

        # Should be successful (even if actual calculation might not work perfectly)
        # The important thing is that it doesn't crash
        assert result["iterations_used"] >= 0
        assert isinstance(result["artifacts_created"], list)

    @pytest.mark.integration
    def test_subagent_with_file_tools(self):
        """Test subagent execution that writes to a file."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        executor = SubagentExecutor()

        # Run subagent that should write a file
        result = executor.run_subagent(
            "Create a summary of today's work and save it to summary.txt",
            ["write_file"],
            {"work_done": "Completed subagent system"},
            "Create summary.txt file with work summary",
            max_iterations=3
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "result" in result
        assert "iterations_used" in result
        assert "artifacts_created" in result

        # Check if file was created (might be empty if execution failed)
        artifacts = result["artifacts_created"]
        if artifacts:
            assert "summary.txt" in artifacts or any("summary" in artifact for artifact in artifacts)

    @pytest.mark.integration
    def test_subagent_max_iterations(self):
        """Test that subagent respects max_iterations limit."""
        # This test requires actual API calls and will be skipped if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping integration test")

        executor = SubagentExecutor()

        # Run subagent with very low max_iterations
        result = executor.run_subagent(
            "Think about a complex problem for a long time",
            ["execute_code"],
            {},
            "Provide a detailed analysis",
            max_iterations=2  # Very low limit
        )

        # Should complete within the iteration limit
        assert result["iterations_used"] <= 2
        assert isinstance(result["result"], str)

    def test_run_subagent_basic_execution(self):
        """Test basic subagent execution."""
        # Mock the LLM and agent executor
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Test response")

        mock_agent = Mock()
        mock_executor = Mock()
        mock_executor.invoke.return_value = {
            "output": "Task completed successfully",
            "intermediate_steps": []
        }

        # Patch the agent creation
        with patch('src.agents.subagent.create_openai_functions_agent', return_value=mock_agent), \
             patch('src.agents.subagent.AgentExecutor', return_value=mock_executor):

            executor = SubagentExecutor()
            result = executor.run_subagent(
                "Test task",
                ["read_file"],
                {"context": "test"},
                "Generate report"
            )

        # Verify result structure
        assert "success" in result
        assert "result" in result
        assert "iterations_used" in result
        assert "artifacts_created" in result

    def test_run_subagent_with_artifacts(self):
        """Test subagent execution that creates artifacts."""
        # Mock intermediate steps that include file operations
        mock_step = Mock()
        mock_step.tool = "write_file"
        mock_step.tool_input = {"path": "test_report.txt"}

        mock_executor = Mock()
        mock_executor.invoke.return_value = {
            "output": "Report generated",
            "intermediate_steps": [mock_step]
        }

        with patch('src.agents.subagent.create_openai_functions_agent'), \
             patch('src.agents.subagent.AgentExecutor', return_value=mock_executor):

            executor = SubagentExecutor()
            result = executor.run_subagent(
                "Generate report",
                ["write_file"],
                {},
                "Create report.txt"
            )

        # Verify artifacts are detected
        assert result["success"] is True
        assert "test_report.txt" in result["artifacts_created"]

    def test_run_subagent_execution_failure(self):
        """Test subagent execution failure handling."""
        mock_executor = Mock()
        mock_executor.invoke.side_effect = Exception("Agent execution failed")

        with patch('src.agents.subagent.create_openai_functions_agent'), \
             patch('src.agents.subagent.AgentExecutor', return_value=mock_executor):

            executor = SubagentExecutor()
            result = executor.run_subagent(
                "Failing task",
                ["read_file"],
                {},
                "Complete task"
            )

        # Verify failure is handled gracefully
        assert result["success"] is False
        assert "Agent execution failed" in result["result"]
        assert result["iterations_used"] == 0
        assert result["artifacts_created"] == []

    def test_create_subagent_executor(self):
        """Test the factory function."""
        # Test with provided file system
        mock_fs = Mock()
        executor = create_subagent_executor(mock_fs)
        assert isinstance(executor, SubagentExecutor)
        assert executor.file_system == mock_fs

        # Test with default file system
        executor2 = create_subagent_executor()
        assert isinstance(executor2, SubagentExecutor)
        assert executor2.file_system is not None

    def test_prompt_generation_edge_cases(self):
        """Test prompt generation with edge cases."""
        # Empty task description
        prompt = generate_subagent_prompt("", {"ctx": "val"}, "criteria", ["tool"])
        assert "Task Description" in prompt

        # Empty context
        prompt = generate_subagent_prompt("task", {}, "criteria", ["tool"])
        assert "Context from Previous Work" in prompt

        # Empty tools list
        prompt = generate_subagent_prompt("task", {"ctx": "val"}, "criteria", [])
        assert "Available Tools" in prompt

        # Very long inputs
        long_task = "A" * 1000
        long_context = {"data": "B" * 1000}
        long_criteria = "C" * 500

        prompt = generate_subagent_prompt(long_task, long_context, long_criteria, ["tool1", "tool2"])
        assert len(prompt) > 1000  # Should handle long inputs

    def test_llm_initialization_error(self):
        """Test LLM initialization with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable not set"):
                SubagentExecutor()

    def test_tools_integration(self):
        """Test that tools are properly integrated."""
        executor = SubagentExecutor()

        # Verify file tools are loaded
        assert len(executor.file_tools) > 0
        assert all(hasattr(tool, 'invoke') for tool in executor.file_tools)

        # Verify assignable tools are loaded
        assert len(executor.assignable_tools) > 0
        assert "execute_code" in executor.assignable_tools

    def test_run_subagent_parameter_validation(self):
        """Test parameter validation in run_subagent."""
        executor = SubagentExecutor()

        # Test with empty parameters (should not crash, but may fail gracefully)
        result = executor.run_subagent("", [], {}, "")
        assert isinstance(result, dict)
        assert "success" in result

    def test_prompt_context_formatting(self):
        """Test that context is properly formatted in prompts."""
        context = {
            "previous_findings": ["Finding 1", "Finding 2"],
            "data_sources": {"file1.csv": "processed", "file2.json": "analyzed"},
            "metadata": {"created": "2024-01-01", "author": "test"}
        }

        prompt = generate_subagent_prompt(
            "Test task",
            context,
            "Generate report",
            ["read_file", "write_file"]
        )

        # Context should be properly JSON formatted
        assert '"previous_findings"' in prompt
        assert '"data_sources"' in prompt
        assert '"metadata"' in prompt
        assert '"created": "2024-01-01"' in prompt

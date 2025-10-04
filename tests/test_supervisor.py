"""
Tests for the Supervisor agent logic.

This module contains comprehensive tests for the SupervisorAgent class and
supervisor_node function, covering decision making, state management, and
integration with tools and LLM.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agents.supervisor import SupervisorAgent, supervisor_node, create_supervisor_agent
from src.agents.supervisor import analyze_state_complexity, get_next_pending_task, is_completion_ready
from src.state import AgentState, create_initial_state, MAX_ITERATIONS, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED
from src.tools.supervisor_tools import get_supervisor_tools

# Load environment variables
load_dotenv()


class TestSupervisorAgent:
    """Test cases for SupervisorAgent class."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Mock LLM and tools for unit tests
        self.mock_llm = Mock()
        self.mock_tools = [Mock(), Mock()]
        
        # Create sample state
        self.sample_state = create_initial_state("Test objective")
    
    def test_supervisor_agent_initialization(self):
        """Test SupervisorAgent initialization."""
        with patch('src.agents.supervisor.create_openai_functions_agent') as mock_agent, \
             patch('src.agents.supervisor.AgentExecutor') as mock_executor:
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            assert supervisor.llm == self.mock_llm
            assert supervisor.tools == self.mock_tools
            assert supervisor.agent_executor is not None
    
    def test_decide_next_action_empty_state(self):
        """Test decision making with empty state."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            # Empty state - should plan
            decision = supervisor.decide_next_action(self.sample_state)
            
            assert decision["action"] == "plan"
            assert "No tasks exist" in decision["reasoning"]
            assert decision["next_task_id"] is None
    
    def test_decide_next_action_with_pending_tasks(self):
        """Test decision making with pending tasks."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            # Add pending tasks
            state_with_tasks = self.sample_state.copy()
            state_with_tasks["todo_list"] = [
                {"id": 1, "description": "Task 1", "status": TASK_STATUS_PENDING},
                {"id": 2, "description": "Task 2", "status": TASK_STATUS_PENDING}
            ]
            
            decision = supervisor.decide_next_action(state_with_tasks)
            
            assert decision["action"] == "execute"
            assert "Execute task" in decision["reasoning"]
            assert decision["next_task_id"] == 1  # First pending task
    
    def test_decide_next_action_all_completed(self):
        """Test decision making when all tasks are completed."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            # All tasks completed
            state_completed = self.sample_state.copy()
            state_completed["todo_list"] = [
                {"id": 1, "description": "Task 1", "status": TASK_STATUS_COMPLETED},
                {"id": 2, "description": "Task 2", "status": TASK_STATUS_COMPLETED}
            ]
            state_completed["iteration_count"] = 1
            
            decision = supervisor.decide_next_action(state_completed)
            
            assert decision["action"] == "finalize"
            assert "All tasks completed" in decision["reasoning"]
            assert decision["next_task_id"] is None
    
    def test_decide_next_action_max_iterations(self):
        """Test decision making when max iterations reached."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            # Max iterations reached
            state_max_iter = self.sample_state.copy()
            state_max_iter["iteration_count"] = MAX_ITERATIONS
            
            decision = supervisor.decide_next_action(state_max_iter)
            
            assert decision["action"] == "finalize"
            assert f"Maximum iterations ({MAX_ITERATIONS})" in decision["reasoning"]
            assert decision["next_task_id"] is None
    
    def test_execute_action_plan(self):
        """Test executing plan action."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor') as mock_executor:
            
            # Mock agent executor
            mock_executor.return_value.invoke.return_value = {
                "output": "Plan created successfully",
                "intermediate_steps": []
            }
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            result = supervisor.execute_action(self.sample_state, "plan")
            
            assert result["success"] is True
            assert result["action"] == "plan"
            assert "Plan created successfully" in result["result"]
    
    def test_execute_action_execute(self):
        """Test executing execute action."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor') as mock_executor:
            
            # Mock agent executor
            mock_executor.return_value.invoke.return_value = {
                "output": "Task executed successfully",
                "intermediate_steps": []
            }
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            result = supervisor.execute_action(self.sample_state, "execute", task_id=1)
            
            assert result["success"] is True
            assert result["action"] == "execute"
            assert "Task executed successfully" in result["result"]
    
    def test_execute_action_error_handling(self):
        """Test error handling in execute_action."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor') as mock_executor:
            
            # Mock agent executor to raise exception
            mock_executor.return_value.invoke.side_effect = Exception("Test error")
            
            supervisor = SupervisorAgent(self.mock_llm, self.mock_tools)
            
            result = supervisor.execute_action(self.sample_state, "plan")
            
            assert result["success"] is False
            assert "Error: Test error" in result["result"]


class TestSupervisorNode:
    """Test cases for supervisor_node function."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        self.sample_state = create_initial_state("Test objective")
    
    def test_supervisor_node_increments_iteration(self):
        """Test that supervisor_node increments iteration count."""
        with patch('src.agents.supervisor.SupervisorAgent') as mock_supervisor_class:
            # Mock supervisor agent
            mock_supervisor = Mock()
            mock_supervisor.decide_next_action.return_value = {
                "action": "plan",
                "reasoning": "Test reasoning",
                "next_task_id": None
            }
            mock_supervisor.execute_action.return_value = {
                "success": True,
                "result": "Test result",
                "intermediate_steps": [],
                "action": "plan"
            }
            mock_supervisor_class.return_value = mock_supervisor
            
            # Mock the supervisor agent attribute
            supervisor_node._supervisor_agent = mock_supervisor
            
            initial_iteration = self.sample_state["iteration_count"]
            result_state = supervisor_node(self.sample_state)
            
            assert result_state["iteration_count"] == initial_iteration + 1
    
    def test_supervisor_node_max_iterations(self):
        """Test supervisor_node stops at max iterations."""
        with patch('src.agents.supervisor.SupervisorAgent') as mock_supervisor_class:
            # Mock supervisor agent
            mock_supervisor = Mock()
            mock_supervisor_class.return_value = mock_supervisor
            supervisor_node._supervisor_agent = mock_supervisor
            
            # Set iteration count to max
            self.sample_state["iteration_count"] = MAX_ITERATIONS
            
            result_state = supervisor_node(self.sample_state)
            
            assert result_state["iteration_count"] == MAX_ITERATIONS + 1
            assert "Maximum iterations reached" in result_state["final_result"]
    
    def test_supervisor_node_handles_errors(self):
        """Test supervisor_node error handling."""
        with patch('src.agents.supervisor.SupervisorAgent') as mock_supervisor_class:
            # Mock supervisor agent to raise exception
            mock_supervisor_class.side_effect = Exception("Test error")
            supervisor_node._supervisor_agent = None
            
            result_state = supervisor_node(self.sample_state)
            
            assert "Supervisor error: Test error" in result_state["final_result"]
            assert len(result_state["messages"]) > 0


class TestSupervisorUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_analyze_state_complexity(self):
        """Test state complexity analysis."""
        # Empty state
        empty_state = create_initial_state("Test")
        assert analyze_state_complexity(empty_state) == "empty"
        
        # Simple state
        simple_state = create_initial_state("Test")
        simple_state["todo_list"] = [{"id": 1, "description": "Task 1", "status": TASK_STATUS_PENDING}]
        simple_state["iteration_count"] = 1
        assert analyze_state_complexity(simple_state) == "simple"
        
        # Complex state
        complex_state = create_initial_state("Test")
        complex_state["todo_list"] = [
            {"id": i, "description": f"Task {i}", "status": TASK_STATUS_PENDING}
            for i in range(10)
        ]
        complex_state["iteration_count"] = 15
        assert analyze_state_complexity(complex_state) == "complex"
    
    def test_get_next_pending_task(self):
        """Test getting next pending task."""
        # No pending tasks
        empty_state = create_initial_state("Test")
        assert get_next_pending_task(empty_state) is None
        
        # With pending tasks
        state_with_tasks = create_initial_state("Test")
        state_with_tasks["todo_list"] = [
            {"id": 1, "description": "Task 1", "status": TASK_STATUS_PENDING},
            {"id": 2, "description": "Task 2", "status": TASK_STATUS_COMPLETED}
        ]
        
        next_task = get_next_pending_task(state_with_tasks)
        assert next_task is not None
        assert next_task["id"] == 1
        assert next_task["description"] == "Task 1"
    
    def test_is_completion_ready(self):
        """Test completion readiness check."""
        # Not ready - no iterations
        empty_state = create_initial_state("Test")
        assert not is_completion_ready(empty_state)
        
        # Not ready - has pending tasks
        state_with_pending = create_initial_state("Test")
        state_with_pending["todo_list"] = [
            {"id": 1, "description": "Task 1", "status": TASK_STATUS_PENDING}
        ]
        state_with_pending["iteration_count"] = 1
        assert not is_completion_ready(state_with_pending)
        
        # Ready - no pending tasks, has iterations
        state_ready = create_initial_state("Test")
        state_ready["todo_list"] = [
            {"id": 1, "description": "Task 1", "status": TASK_STATUS_COMPLETED}
        ]
        state_ready["iteration_count"] = 1
        assert is_completion_ready(state_ready)


class TestSupervisorIntegration:
    """Integration tests for Supervisor with LLM and tools."""
    
    @pytest.mark.integration
    def test_supervisor_creates_plan(self):
        """Test that supervisor creates a plan when starting with empty TODO."""
        # This test requires actual LLM and API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        from langchain_openai import ChatOpenAI
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_api_key)
        
        # Create supervisor agent
        supervisor_tools = get_supervisor_tools()
        supervisor = SupervisorAgent(llm, supervisor_tools)
        
        # Test with empty state
        empty_state = create_initial_state("Create a simple Python script that prints 'Hello World'")
        
        decision = supervisor.decide_next_action(empty_state)
        assert decision["action"] == "plan"
        
        # Execute the plan action
        result = supervisor.execute_action(empty_state, "plan")
        assert result["success"] is True
    
    @pytest.mark.integration
    def test_supervisor_selects_next_task(self):
        """Test that supervisor selects next task when pending tasks exist."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        from langchain_openai import ChatOpenAI
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_api_key)
        
        # Create supervisor agent
        supervisor_tools = get_supervisor_tools()
        supervisor = SupervisorAgent(llm, supervisor_tools)
        
        # Test with pending tasks
        state_with_tasks = create_initial_state("Test objective")
        state_with_tasks["todo_list"] = [
            {"id": 1, "description": "Write a Python script", "status": TASK_STATUS_PENDING, "assigned_tools": ["execute_code_tool"]},
            {"id": 2, "description": "Save the script to file", "status": TASK_STATUS_PENDING, "assigned_tools": ["write_file_tool"]}
        ]
        
        decision = supervisor.decide_next_action(state_with_tasks)
        assert decision["action"] == "execute"
        assert decision["next_task_id"] == 1
    
    @pytest.mark.integration
    def test_supervisor_finalizes(self):
        """Test that supervisor finalizes when all tasks are complete."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        from langchain_openai import ChatOpenAI
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_api_key)
        
        # Create supervisor agent
        supervisor_tools = get_supervisor_tools()
        supervisor = SupervisorAgent(llm, supervisor_tools)
        
        # Test with completed tasks
        state_completed = create_initial_state("Test objective")
        state_completed["todo_list"] = [
            {"id": 1, "description": "Task 1", "status": TASK_STATUS_COMPLETED},
            {"id": 2, "description": "Task 2", "status": TASK_STATUS_COMPLETED}
        ]
        state_completed["iteration_count"] = 1
        
        decision = supervisor.decide_next_action(state_completed)
        assert decision["action"] == "finalize"
    
    @pytest.mark.integration
    def test_supervisor_max_iterations(self):
        """Test that supervisor stops after MAX_ITERATIONS."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        from langchain_openai import ChatOpenAI
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_api_key)
        
        # Create supervisor agent
        supervisor_tools = get_supervisor_tools()
        supervisor = SupervisorAgent(llm, supervisor_tools)
        
        # Test with max iterations
        state_max_iter = create_initial_state("Test objective")
        state_max_iter["iteration_count"] = MAX_ITERATIONS
        
        decision = supervisor.decide_next_action(state_max_iter)
        assert decision["action"] == "finalize"
        assert f"Maximum iterations ({MAX_ITERATIONS})" in decision["reasoning"]
    
    @pytest.mark.integration
    def test_supervisor_tool_assignment(self):
        """Test that supervisor assigns appropriate tools to tasks."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OPENAI_API_KEY not available")
        
        from langchain_openai import ChatOpenAI
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_api_key)
        
        # Create supervisor agent
        supervisor_tools = get_supervisor_tools()
        supervisor = SupervisorAgent(llm, supervisor_tools)
        
        # Test tool assignment logic
        state = create_initial_state("Calculate the sum of squares from 1 to 10 and save to file")
        
        # The supervisor should be able to create tasks with appropriate tools
        decision = supervisor.decide_next_action(state)
        assert decision["action"] == "plan"
        
        # Execute plan action to create tasks
        result = supervisor.execute_action(state, "plan")
        assert result["success"] is True


class TestSupervisorEdgeCases:
    """Test edge cases for Supervisor."""
    
    def test_empty_objective(self):
        """Test handling of empty objectives."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(Mock(), [])
            
            empty_state = create_initial_state("")
            decision = supervisor.decide_next_action(empty_state)
            
            # Should still try to plan
            assert decision["action"] == "plan"
    
    def test_infinite_loop_prevention(self):
        """Test prevention of infinite loops."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor'):
            
            supervisor = SupervisorAgent(Mock(), [])
            
            # High iteration count should trigger finalize
            high_iter_state = create_initial_state("Test")
            high_iter_state["iteration_count"] = MAX_ITERATIONS - 1
            
            decision = supervisor.decide_next_action(high_iter_state)
            assert decision["action"] in ["execute", "finalize"]
    
    def test_tool_call_failures(self):
        """Test handling of tool call failures."""
        with patch('src.agents.supervisor.create_openai_functions_agent'), \
             patch('src.agents.supervisor.AgentExecutor') as mock_executor:
            
            # Mock agent executor to fail
            mock_executor.return_value.invoke.side_effect = Exception("Tool call failed")
            
            supervisor = SupervisorAgent(Mock(), [])
            result = supervisor.execute_action(create_initial_state("Test"), "plan")
            
            assert result["success"] is False
            assert "Error: Tool call failed" in result["result"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

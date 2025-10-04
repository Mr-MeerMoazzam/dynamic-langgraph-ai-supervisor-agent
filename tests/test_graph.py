"""Tests for LangGraph workflow"""

import pytest
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.workflow import create_workflow, create_initial_state, graph


def test_graph_creation():
    """Test that graph can be created"""
    workflow = create_workflow()
    compiled_graph = workflow.compile()
    assert compiled_graph is not None


def test_state_schema():
    """Test state has correct schema"""
    state = create_initial_state("Test objective")
    
    assert "objective" in state
    assert "todo_list" in state
    assert "completed_tasks" in state
    assert "iteration_count" in state
    assert state["iteration_count"] == 0
    assert state["objective"] == "Test objective"


def test_initial_state_creation():
    """Test initial state creation with different parameters"""
    # Test with default max_iterations
    state1 = create_initial_state("Test 1")
    assert state1["max_iterations"] == 20
    
    # Test with custom max_iterations
    state2 = create_initial_state("Test 2", max_iterations=10)
    assert state2["max_iterations"] == 10
    
    # Test state structure
    for state in [state1, state2]:
        assert isinstance(state["todo_list"], list)
        assert isinstance(state["completed_tasks"], list)
        assert isinstance(state["current_task"], dict)
        assert state["iteration_count"] == 0
        assert state["final_result"] == ""


@pytest.mark.integration
def test_simple_workflow():
    """Test workflow with simple objective (requires API keys)"""
    # This test requires API keys to be set
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skipping integration test")
    
    workflow = create_workflow()
    compiled_graph = workflow.compile()
    
    state = create_initial_state(
        objective="Create test.txt with 'hello world'",
        max_iterations=5
    )
    
    result = compiled_graph.invoke(state)
    
    assert result["iteration_count"] > 0
    assert result["iteration_count"] <= 5


def test_graph_compilation():
    """Test that the global graph object is properly compiled"""
    assert graph is not None
    # Test that we can access the graph's nodes
    assert hasattr(graph, 'nodes')
    # Test that the graph is properly compiled
    assert hasattr(graph, 'invoke')


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Demonstration of the Task Executor functionality.

This script shows how the Task Executor handles task execution, state updates,
artifact tracking, and error handling in the Supervisor Agent system.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agents.task_executor import (
    validate_task_execution, get_task_execution_summary, create_task_execution_context,
    format_task_execution_result, _prepare_task_context, _define_success_criteria
)
from src.state import create_initial_state, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED

def demonstrate_task_validation():
    """Demonstrate task execution validation."""
    print("🔍 TASK EXECUTION VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    # Test 1: Valid task
    print("\n1. VALID TASK")
    print("-" * 30)
    valid_state = create_initial_state("Test objective")
    valid_state["current_task"] = {
        "id": 1,
        "description": "Calculate fibonacci(10)",
        "assigned_tools": ["execute_code_tool"],
        "status": TASK_STATUS_PENDING
    }
    
    is_valid = validate_task_execution(valid_state)
    print(f"   Task validation: {is_valid}")
    print("   ✅ All required fields present")
    
    # Test 2: Invalid task (missing fields)
    print("\n2. INVALID TASK (Missing Fields)")
    print("-" * 30)
    invalid_state = create_initial_state("Test objective")
    invalid_state["current_task"] = {
        "id": 1
        # Missing description and assigned_tools
    }
    
    is_valid = validate_task_execution(invalid_state)
    print(f"   Task validation: {is_valid}")
    print("   ❌ Missing required fields")
    
    # Test 3: No current task
    print("\n3. NO CURRENT TASK")
    print("-" * 30)
    no_task_state = create_initial_state("Test objective")
    # No current_task set
    
    is_valid = validate_task_execution(no_task_state)
    print(f"   Task validation: {is_valid}")
    print("   ❌ No current task to execute")

def demonstrate_context_preparation():
    """Demonstrate context preparation for task execution."""
    print("\n\n📋 CONTEXT PREPARATION DEMONSTRATION")
    print("=" * 60)
    
    # Create state with completed tasks
    state = create_initial_state("Build a complete web application")
    state["iteration_count"] = 5
    state["completed_tasks"] = [
        {
            "id": 1,
            "task": "Research web frameworks",
            "result": "Found 3 suitable frameworks",
            "artifacts": ["research.txt"],
            "status": TASK_STATUS_COMPLETED
        },
        {
            "id": 2,
            "task": "Choose framework",
            "result": "Selected React for frontend",
            "artifacts": ["decision.txt"],
            "status": TASK_STATUS_COMPLETED
        }
    ]
    state["todo_list"] = [
        {"id": 3, "description": "Setup development environment", "status": TASK_STATUS_PENDING},
        {"id": 4, "description": "Create basic project structure", "status": TASK_STATUS_PENDING}
    ]
    
    # Prepare context
    context = _prepare_task_context(state)
    
    print("Prepared context:")
    for key, value in context.items():
        if key == "recent_completed_tasks":
            print(f"   {key}: {len(value)} tasks")
            for task in value:
                print(f"     - {task['description']}: {task['result'][:50]}...")
        else:
            print(f"   {key}: {value}")

def demonstrate_success_criteria():
    """Demonstrate success criteria definition."""
    print("\n\n🎯 SUCCESS CRITERIA DEMONSTRATION")
    print("=" * 60)
    
    # Test different task types
    task_scenarios = [
        {
            "description": "Calculate the sum of squares from 1 to 10",
            "assigned_tools": ["execute_code_tool"],
            "expected": "execution results"
        },
        {
            "description": "Research AI agents online",
            "assigned_tools": ["search_internet_tool"],
            "expected": "relevant information found"
        },
        {
            "description": "Create a report document",
            "assigned_tools": ["write_file_tool"],
            "expected": "save any important results to files"
        },
        {
            "description": "Extract content from webpage",
            "assigned_tools": ["web_scrape_tool"],
            "expected": "extract the requested content"
        }
    ]
    
    for i, scenario in enumerate(task_scenarios, 1):
        print(f"\n{i}. {scenario['description']}")
        print(f"   Tools: {scenario['assigned_tools']}")
        
        current_task = {
            "description": scenario["description"],
            "assigned_tools": scenario["assigned_tools"]
        }
        
        success_criteria = _define_success_criteria(current_task, create_initial_state("Test"))
        print(f"   Success criteria: {success_criteria}")
        print(f"   ✅ Contains: {scenario['expected']}")

def demonstrate_execution_summary():
    """Demonstrate task execution summary."""
    print("\n\n📊 TASK EXECUTION SUMMARY DEMONSTRATION")
    print("=" * 60)
    
    # Create state with mixed results
    state = create_initial_state("Complete project")
    state["completed_tasks"] = [
        {
            "id": 1,
            "task": "Setup project",
            "status": TASK_STATUS_COMPLETED,
            "artifacts": ["package.json", "README.md"]
        },
        {
            "id": 2,
            "task": "Write tests",
            "status": TASK_STATUS_COMPLETED,
            "artifacts": ["test_suite.py"]
        },
        {
            "id": 3,
            "task": "Deploy to production",
            "status": TASK_STATUS_FAILED,
            "artifacts": []
        }
    ]
    state["todo_list"] = [
        {"id": 4, "description": "Write documentation", "status": TASK_STATUS_PENDING},
        {"id": 5, "description": "Performance optimization", "status": TASK_STATUS_PENDING}
    ]
    
    summary = get_task_execution_summary(state)
    
    print("Execution Summary:")
    print(f"   Total tasks: {summary['total_tasks']}")
    print(f"   Completed: {summary['completed_tasks']}")
    print(f"   Successful: {summary['successful_tasks']}")
    print(f"   Failed: {summary['failed_tasks']}")
    print(f"   Pending: {summary['pending_tasks']}")
    print(f"   Total artifacts: {summary['total_artifacts']}")
    print(f"   Completion rate: {summary['completion_rate']:.1f}%")
    print(f"   Success rate: {summary['success_rate']:.1f}%")

def demonstrate_result_formatting():
    """Demonstrate result formatting."""
    print("\n\n📝 RESULT FORMATTING DEMONSTRATION")
    print("=" * 60)
    
    # Test successful result
    print("1. SUCCESSFUL TASK RESULT")
    print("-" * 30)
    success_result = {
        "success": True,
        "result": "Task completed successfully with detailed analysis and comprehensive results",
        "artifacts": ["analysis.txt", "results.json", "summary.pdf"],
        "details": "All operations completed without errors and data was processed correctly"
    }
    
    formatted = format_task_execution_result(1, "Analyze sales data", success_result)
    print(formatted)
    
    # Test failed result
    print("\n2. FAILED TASK RESULT")
    print("-" * 30)
    failure_result = {
        "success": False,
        "result": "Task failed due to insufficient data",
        "artifacts": [],
        "details": "Error: Data source returned empty results"
    }
    
    formatted = format_task_execution_result(2, "Generate report", failure_result)
    print(formatted)

def demonstrate_task_executor_workflow():
    """Demonstrate the complete task executor workflow."""
    print("\n\n🔄 TASK EXECUTOR WORKFLOW DEMONSTRATION")
    print("=" * 60)
    
    print("The Task Executor follows this workflow:")
    print("1. 📋 Validate current task (check required fields)")
    print("2. 🧠 Prepare context (gather relevant information)")
    print("3. 🎯 Define success criteria (based on task and tools)")
    print("4. 🛠️ Execute task (using task_tool with subagent)")
    print("5. 📊 Update state (move to completed, track artifacts)")
    print("6. 📝 Log results (add messages and summary)")
    
    print("\nKey Features:")
    print("✅ Intelligent context preparation")
    print("✅ Tool-specific success criteria")
    print("✅ Comprehensive artifact tracking")
    print("✅ Graceful error handling")
    print("✅ Detailed execution logging")
    print("✅ State management and updates")

def main():
    """Main demonstration function."""
    load_dotenv()
    
    print("🎯 TASK EXECUTOR SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demonstration shows how the Task Executor handles")
    print("task execution, state updates, and result tracking.")
    print()
    
    # Demonstrate core functionality
    demonstrate_task_validation()
    demonstrate_context_preparation()
    demonstrate_success_criteria()
    demonstrate_execution_summary()
    demonstrate_result_formatting()
    demonstrate_task_executor_workflow()
    
    print("\n" + "=" * 60)
    print("🎉 DEMONSTRATION COMPLETE")
    print("The Task Executor is ready to handle task execution!")
    print("Key features: Context preparation, success criteria,")
    print("artifact tracking, error handling, and state management.")
    print("=" * 60)

if __name__ == "__main__":
    main()

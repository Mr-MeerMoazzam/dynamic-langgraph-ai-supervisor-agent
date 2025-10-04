#!/usr/bin/env python3
"""
Complete example demonstrating task_tool usage for the Supervisor Agent system.

This example shows how to use the task_tool to create and execute a specialized
subagent that performs a mathematical calculation and saves results to a file.

The example demonstrates:
- Loading environment variables for API access
- Creating a task with multiple tools (execute_code + write_file)
- Providing context and success criteria
- Executing the task and checking results
- Verifying file creation in the VirtualFileSystem

Usage:
    python examples/test_task_tool.py

Note: Requires OPENAI_API_KEY environment variable to be set.
"""

import os
import sys
from typing import Dict, Any

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  dotenv not available - using system environment variables")

# Check for required API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("❌ OPENAI_API_KEY environment variable not set")
    print("   Please set your OpenAI API key in the .env file or system environment")
    sys.exit(1)

print(f"✅ OpenAI API key loaded (length: {len(openai_api_key)})")


def main():
    """
    Demonstrate task_tool usage with a complete mathematical calculation example.

    This example shows how the Supervisor Agent would use task_tool to execute
    specialized subagents. In practice:

    1. The Supervisor analyzes the current objective and state
    2. It determines which tools are needed for the task
    3. It provides relevant context from previous work
    4. It defines clear success criteria
    5. The task_tool creates and executes a specialized subagent
    6. Results are analyzed and artifacts are tracked

    Note: In the actual Supervisor Agent implementation, tool assignment and
    context would be determined automatically based on the current state and
    objective requirements.
    """

    print("\n" + "="*60)
    print("TASK_TOOL DEMONSTRATION")
    print("="*60)

    # Step 1: Import required components
    print("\n1. Importing components...")
    from src.tools.supervisor_tools import task_tool
    from src.file_system import VirtualFileSystem

    print("   ✅ Imported task_tool and VirtualFileSystem")

    # Step 2: Define the task (as Supervisor would)
    print("\n2. Task definition (as Supervisor would determine)...")

    # In practice, the Supervisor would:
    # - Analyze current objective: "Calculate mathematical sequences"
    # - Determine required tools: execute_code for calculation, write_file for output
    # - Gather context from previous tasks or state
    # - Define success criteria based on requirements

    task_description = "Calculate the sum of squares from 1 to 10 and save to results.txt"
    print(f"   Task: {task_description}")

    # Supervisor determines which tools are needed
    assigned_tools = ["execute_code", "write_file_tool"]  # execute_code for math, write_file_tool for output
    print(f"   Tools: {assigned_tools}")

    # Context would come from current state or previous tasks
    context = {
        "calculation_type": "sum_of_squares",
        "range_start": 1,
        "range_end": 10,
        "output_file": "results.txt",
        "previous_findings": "Need to calculate mathematical sequences"
    }
    print(f"   Context: {context}")

    # Success criteria defined by Supervisor based on objective
    success_criteria = "Create results.txt with the calculated sum of squares (1² + 2² + ... + 10²)"
    print(f"   Success Criteria: {success_criteria}")

    # Step 3: Execute the task
    print("\n3. Executing task via task_tool...")

    try:
        result = task_tool.invoke({
            "task_description": task_description,
            "assigned_tools": assigned_tools,
            "context": context,
            "success_criteria": success_criteria
        })

        print("   ✅ Task execution completed")

        # Step 4: Analyze results
        print("\n4. Analyzing results...")

        print(f"   Success: {result['success']}")
        print(f"   Iterations used: {result['details']}")

        if result['artifacts']:
            print(f"   Artifacts created: {result['artifacts']}")
        else:
            print("   No artifacts created")

        # Step 5: Verify file creation in VirtualFileSystem
        print("\n5. Checking VirtualFileSystem for created files...")

        vfs = VirtualFileSystem()

        # Check if results.txt was created
        if "results.txt" in vfs.list_files():
            print("   ✅ results.txt found in VirtualFileSystem")

            # Read and display the file content
            content = vfs.read_file("results.txt")
            print(f"   File content ({len(content)} characters):")
            print("   " + "-"*50)
            print(f"   {content}")
            print("   " + "-"*50)
        else:
            print("   ⚠️  results.txt not found in VirtualFileSystem")

        # Show all files in the system
        all_files = vfs.list_files()
        if all_files:
            print(f"   All files in VFS: {all_files}")
        else:
            print("   No files in VirtualFileSystem")

        # Step 6: Summary
        print("\n6. Summary...")

        if result['success']:
            print("   ✅ Task completed successfully!")
            print("   ✅ File operations working correctly")
            print("   ✅ Subagent execution functional")
            print("   ✅ Context engineering operational")
        else:
            print("   ⚠️  Task completed but may have had issues")
            print(f"   Result: {result['result']}")

        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETE")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n❌ Task execution failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print("   Full traceback:")
        print("   " + "\n   ".join(traceback.format_exc().split('\n')))
        return False


def demonstrate_error_handling():
    """
    Demonstrate error handling in task_tool.

    This shows how the task_tool handles various error scenarios.
    """
    print("\n" + "="*60)
    print("ERROR HANDLING DEMONSTRATION")
    print("="*60)

    from src.tools.supervisor_tools import task_tool

    # Test 1: Invalid tools
    print("\n1. Testing invalid tool assignment...")
    result = task_tool.invoke({
        "task_description": "Test task",
        "assigned_tools": ["invalid_tool_name"],
        "context": {},
        "success_criteria": "Complete task"
    })

    if not result["success"]:
        print(f"   ✅ Correctly rejected invalid tool: {result['details']}")
    else:
        print("   ❌ Should have rejected invalid tool")

    # Test 2: Missing context validation
    print("\n2. Testing missing context...")
    try:
        result = task_tool.invoke({
            "task_description": "Test task",
            "assigned_tools": ["execute_code"],
            "context": "not a dict",  # Invalid context type
            "success_criteria": "Complete task"
        })
        print(f"   ❌ Should have caught validation error, but got: {result}")
    except Exception as e:
        print(f"   ✅ Correctly caught validation error: {type(e).__name__}: {str(e)[:100]}...")


if __name__ == "__main__":
    print("SUPERVISOR AGENT - TASK_TOOL DEMONSTRATION")
    print("="*60)

    # Run the main demonstration
    success = main()

    # Demonstrate error handling
    demonstrate_error_handling()

    print("\n" + "="*60)
    if success:
        print("🎉 DEMONSTRATION SUCCESSFUL!")
        print("   The task_tool is working correctly with the Supervisor Agent system.")
    else:
        print("⚠️  DEMONSTRATION COMPLETED WITH ISSUES")
        print("   Check the error messages above for troubleshooting.")
    print("="*60)

    # Exit with appropriate code
    exit(0 if success else 1)

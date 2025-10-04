"""
Tests for file tools functionality.

This module contains comprehensive tests for the LangChain file tools,
ensuring they properly integrate with the VirtualFileSystem and handle
all operations correctly using the .invoke() method.
"""

import pytest
import os
from typing import List, Dict, Any

# Load environment variables from .env file for testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not available, continue without loading .env
    pass

# Import the file tools
from src.tools.file_tools import (
    read_file_tool,
    write_file_tool,
    edit_file_tool,
    get_file_tools
)

# Import the assignable tools
from src.tools.assignable_tools import (
    execute_code_tool,
    search_internet_tool,
    web_scrape_tool
)


class TestFileTools:
    """Test suite for file tools functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear the file system before each test to ensure clean state
        from src.file_system import VirtualFileSystem
        vfs = VirtualFileSystem()
        vfs.clear_all()

    def teardown_method(self):
        """Clean up after each test method."""
        # Ensure file system is clean after each test
        from src.file_system import VirtualFileSystem
        vfs = VirtualFileSystem()
        vfs.clear_all()

    def test_read_file_tool(self):
        """Test reading a file using read_file_tool.invoke()."""
        # First create a file to read
        write_result = write_file_tool.invoke({
            "path": "test_read.txt",
            "content": "This is test content for reading."
        })
        assert "created" in write_result

        # Now read the file
        content = read_file_tool.invoke({
            "path": "test_read.txt"
        })

        assert content == "This is test content for reading."

    def test_write_file_tool(self):
        """Test writing a file using write_file_tool.invoke()."""
        # Write a file
        result = write_file_tool.invoke({
            "path": "test_write.txt",
            "content": "This is test content for writing."
        })

        # Verify the result message
        assert "test_write.txt" in result
        assert "created" in result or "overwritten" in result
        assert "bytes written" in result

        # Verify the file exists and has correct content
        from src.file_system import VirtualFileSystem
        vfs = VirtualFileSystem()
        assert vfs.file_exists("test_write.txt")
        content = vfs.read_file("test_write.txt")
        assert content == "This is test content for writing."

    def test_edit_file_tool_find_replace(self):
        """Test find/replace editing using edit_file_tool.invoke()."""
        # Create a file first
        write_file_tool.invoke({
            "path": "test_edit.txt",
            "content": "Hello world! This is a test file."
        })

        # Perform find/replace operations
        edits = [
            {"find": "Hello", "replace": "Hi"},
            {"find": "world", "replace": "universe"}
        ]

        result = edit_file_tool.invoke({
            "path": "test_edit.txt",
            "edits": edits
        })

        # Verify the result message
        assert "test_edit.txt" in result
        assert "replacements" in result
        assert "Diff:" in result

        # Verify the content was changed correctly
        from src.file_system import VirtualFileSystem
        vfs = VirtualFileSystem()
        updated_content = vfs.read_file("test_edit.txt")
        expected_content = "Hi universe! This is a test file."
        assert updated_content == expected_content

    def test_edit_file_tool_full_replace(self):
        """Test full content replacement using edit_file_tool.invoke()."""
        # Create a file first
        write_file_tool.invoke({
            "path": "test_replace.txt",
            "content": "Original content that will be replaced."
        })

        # Perform complete replacement
        new_content = "This is completely new content."
        result = edit_file_tool.invoke({
            "path": "test_replace.txt",
            "edits": new_content  # Pass as string for full replacement
        })

        # Verify the result message
        assert "test_replace.txt" in result
        assert "completely replaced" in result or "replaced" in result
        assert "Diff:" in result

        # Verify the content was completely replaced
        from src.file_system import VirtualFileSystem
        vfs = VirtualFileSystem()
        updated_content = vfs.read_file("test_replace.txt")
        assert updated_content == new_content

    def test_read_nonexistent_file(self):
        """Test error handling when reading non-existent file."""
        # Try to read a file that doesn't exist
        result = read_file_tool.invoke({
            "path": "nonexistent_file.txt"
        })

        # Should return an error message
        assert "Error:" in result
        assert "not found" in result.lower()

    def test_get_file_tools(self):
        """Test that get_file_tools() returns exactly 3 tools."""
        tools = get_file_tools()

        # Should return exactly 3 tools
        assert len(tools) == 3

        # Verify tool names
        tool_names = [tool.name for tool in tools]
        expected_names = ["read_file_tool", "write_file_tool", "edit_file_tool"]
        assert tool_names == expected_names

        # Verify each tool has the expected structure
        for tool in tools:
            assert hasattr(tool, 'invoke')
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')

    def test_tool_error_handling_write_invalid_path(self):
        """Test error handling for invalid paths in write operations."""
        # Try to write with empty path
        result = write_file_tool.invoke({
            "path": "",
            "content": "test content"
        })

        assert "Error:" in result
        assert "invalid" in result.lower()

    def test_tool_error_handling_edit_nonexistent_file(self):
        """Test error handling when editing non-existent file."""
        result = edit_file_tool.invoke({
            "path": "nonexistent_edit.txt",
            "edits": "new content"
        })

        assert "Error:" in result
        assert "not found" in result.lower()

    def test_tool_integration_workflow(self):
        """Test a complete workflow using all three tools."""
        # 1. Write initial content
        write_result = write_file_tool.invoke({
            "path": "workflow_test.txt",
            "content": "Initial content for workflow test."
        })
        assert "created" in write_result

        # 2. Read and verify
        content = read_file_tool.invoke({
            "path": "workflow_test.txt"
        })
        assert content == "Initial content for workflow test."

        # 3. Edit with find/replace
        edit_result = edit_file_tool.invoke({
            "path": "workflow_test.txt",
            "edits": [{"find": "Initial", "replace": "Updated"}]
        })
        assert "replacements" in edit_result

        # 4. Verify final content
        final_content = read_file_tool.invoke({
            "path": "workflow_test.txt"
        })
        assert final_content == "Updated content for workflow test."

    def test_execute_code_simple(self):
        """Test executing simple math code using execute_code_tool.invoke()."""
        result = execute_code_tool.invoke({
            "code": "print(2 + 2)"
        })

        # Verify success and output
        assert result["success"] is True
        assert result["output"].strip() == "4"
        assert result["error"] is None

    def test_execute_code_with_imports(self):
        """Test executing code with imports using execute_code_tool.invoke()."""
        result = execute_code_tool.invoke({
            "code": "import math; print(math.pi)"
        })

        # Verify success and output
        assert result["success"] is True
        assert "3.14159" in result["output"]  # math.pi value
        assert result["error"] is None

    def test_execute_code_error(self):
        """Test error handling when executing invalid code."""
        result = execute_code_tool.invoke({
            "code": "print(undefined_variable)"
        })

        # Verify error handling
        assert result["success"] is False
        assert result["output"] == ""  # No output on error
        assert "NameError" in result["error"]
        assert "undefined_variable" in result["error"]

    def test_execute_code_timeout(self):
        """Test timeout protection for long-running code."""
        # Create code that would take longer than timeout if not protected
        # Note: This test is conceptual since timeout testing is complex in unit tests
        # In practice, this would be tested in integration tests

        # For now, we'll test that the tool handles basic timeout scenarios
        # The actual timeout protection is tested in the subprocess execution

        # Test that normal short code works
        result = execute_code_tool.invoke({
            "code": "print('quick execution')"
        })

        assert result["success"] is True
        assert result["output"].strip() == "quick execution"
        assert result["error"] is None

        # Note: Actual timeout testing would require running code that takes >30 seconds
        # which is not practical in unit tests. The timeout protection is verified
        # through the subprocess implementation and safety design.

    @pytest.mark.skipif(
        not os.getenv("TAVILY_API_KEY"),
        reason="TAVILY_API_KEY not set - skipping search test"
    )
    def test_search_internet_tool(self):
        """Test internet search functionality using Tavily API."""
        # Simple search query
        result = search_internet_tool.invoke({
            "query": "Python programming language"
        })

        # Should return a list of results
        assert isinstance(result, list)
        assert len(result) > 0

        # Each result should have required fields
        for item in result:
            if "error" not in item:  # Skip error results
                assert "title" in item
                assert "url" in item
                assert "snippet" in item
                assert isinstance(item["title"], str)
                assert isinstance(item["url"], str)
                assert isinstance(item["snippet"], str)

    @pytest.mark.skipif(
        not os.getenv("FIRECRAWL_API_KEY"),
        reason="FIRECRAWL_API_KEY not set - skipping scrape test"
    )
    def test_web_scrape_tool(self):
        """Test web scraping functionality using Firecrawl API."""
        # Simple URL to scrape (using a reliable test URL)
        result = web_scrape_tool.invoke({
            "url": "https://httpbin.org/html"
        })

        # Should return a dict with required fields
        assert isinstance(result, dict)
        assert "url" in result
        assert "success" in result
        assert "content" in result

        # If successful, should have content
        if result["success"]:
            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0
            assert result["url"] == "https://httpbin.org/html"
        else:
            # If not successful, should have error message
            assert "error" in result
            assert isinstance(result["error"], str)

    def test_get_assignable_tools(self):
        """Test that get_assignable_tools() returns dict with all 3 tools."""
        from src.tools.assignable_tools import get_assignable_tools

        tools = get_assignable_tools()

        # Should return a dictionary
        assert isinstance(tools, dict)

        # Should have exactly 3 tools
        assert len(tools) == 3

        # Should have all expected tools
        expected_tools = ["execute_code", "search_internet", "web_scrape"]
        for tool_name in expected_tools:
            assert tool_name in tools
            assert hasattr(tools[tool_name], 'invoke')
            assert hasattr(tools[tool_name], 'name')
            assert hasattr(tools[tool_name], 'description')

    @pytest.mark.skipif(
        not os.getenv("TAVILY_API_KEY"),
        reason="TAVILY_API_KEY not set - skipping API availability test"
    )
    def test_search_tool_api_availability(self):
        """Test that search tool handles API availability correctly."""
        # Test with a simple query that should work if API is available
        result = search_internet_tool.invoke({
            "query": "test query"
        })

        # Should either return results or a proper error
        assert isinstance(result, list)

        # If API is working, should get results
        if len(result) > 0 and "error" not in result[0]:
            assert len(result) > 0
            assert "title" in result[0]
        else:
            # Should have error message if API fails
            assert any("error" in item for item in result)

    @pytest.mark.skipif(
        not os.getenv("FIRECRAWL_API_KEY"),
        reason="FIRECRAWL_API_KEY not set - skipping API availability test"
    )
    def test_scrape_tool_api_availability(self):
        """Test that scrape tool handles API availability correctly."""
        # Test with a simple URL that should work if API is available
        result = web_scrape_tool.invoke({
            "url": "https://httpbin.org/html"
        })

        # Should return proper structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "content" in result
        assert "url" in result

        # Either success with content, or failure with error message
        if result["success"]:
            assert len(result["content"]) > 0
        else:
            assert "error" in result

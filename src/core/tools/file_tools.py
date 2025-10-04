"""
LangChain tools for file operations using VirtualFileSystem.

This module provides three LangChain tools that wrap the VirtualFileSystem
functionality, allowing agents to read, write, and edit files as part of
their context engineering process.

The tools are designed to be used by LangGraph agents for externalized
memory and state management, enabling agents to persist findings,
intermediate results, and artifacts during complex multi-step tasks.
"""

from typing import List, Dict, Union, Any
from langchain.tools import tool

# Import the VirtualFileSystem singleton
from src.core.file_system import VirtualFileSystem


@tool
def read_file_tool(path: str) -> str:
    """
    Read the content of a file from the virtual file system.

    This tool allows agents to retrieve the contents of any file stored in the
    virtual file system. Files are identified by their path, and the tool
    provides access to the complete file content as a string.

    Use this tool when you need to:
    - Review previously stored information or artifacts
    - Access intermediate results from earlier tasks
    - Read configuration files or data files
    - Examine code or documentation that was saved

    Args:
        path: The path to the file to read (e.g., "data/sales_report.txt")

    Returns:
        str: The complete content of the file

    Raises:
        FileNotFoundError: If the specified file does not exist
        ValueError: If the path is invalid or empty

    Example:
        >>> content = read_file_tool("analysis/findings.txt")
        >>> print(content)  # Prints the file content
    """
    try:
        vfs = VirtualFileSystem()
        return vfs.read_file(path)
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error reading file: {str(e)}"


@tool
def write_file_tool(path: str, content: str) -> str:
    """
    Write content to a file in the virtual file system.

    This tool allows agents to create new files or overwrite existing files
    with new content. The tool handles both file creation and updates,
    providing feedback on whether a file was created or overwritten.

    Use this tool when you need to:
    - Save analysis results or findings
    - Create reports or documentation
    - Store intermediate data for later use
    - Persist code snippets or configurations
    - Create artifacts from processing tasks

    Args:
        path: The path where to save the file (e.g., "reports/final_analysis.txt")
        content: The content to write to the file

    Returns:
        str: Success message with file path, bytes written, and creation status

    Raises:
        ValueError: If path or content are invalid

    Example:
        >>> result = write_file_tool("results/summary.txt", "Analysis complete.")
        >>> print(result)  # "File 'results/summary.txt' created (18 bytes written)"
    """
    try:
        vfs = VirtualFileSystem()
        result = vfs.write_file(path, content)

        status_msg = "created" if result['status'] == 'created' else "overwritten"
        return f"File '{result['path']}' {status_msg} ({result['bytes_written']} bytes written)"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error writing file: {str(e)}"


@tool
def edit_file_tool(path: str, edits: Union[List[Dict[str, str]], str], mode: str = "auto") -> str:
    """
    Edit an existing file using different strategies based on your needs.
    
    IMPORTANT USAGE GUIDELINES:
    - To ADD content to end of file: mode="append"
    - To REPLACE specific text: mode="find_replace" with list of edits
    - To REPLACE entire file: mode="replace" with new content string
    - mode="auto" (default): Infers from edits type
    
    Args:
        path: Path to the file to edit (must already exist)
        edits: Either:
            - String: For append or replace operations
            - List of {"find": str, "replace": str}: For targeted find/replace
        mode: "auto", "find_replace", "append", or "replace"
    
    Returns:
        Success message with diff showing changes
        
    Examples:
        # APPEND new function to existing code
        edit_file_tool("calculator.py", '''
def new_function():
    pass
''', mode="append")
        
        # FIND/REPLACE specific values
        edit_file_tool("config.txt", [
            {"find": "debug=false", "replace": "debug=true"},
            {"find": "port=8000", "replace": "port=3000"}
        ], mode="find_replace")
        
        # REPLACE entire file
        edit_file_tool("readme.txt", "New complete content", mode="replace")
        
    Common mistakes to avoid:
    - Don't use replace mode when you want to add to a file - use append
    - Don't use append when you want to change specific values - use find_replace
    - Always check file content with read_file_tool before editing
    """
    from typing import Union, List, Dict
    from src.core.file_system import VirtualFileSystem
    
    fs = VirtualFileSystem()
    result = fs.edit_file(path, edits, mode)
    
    if result.get('success'):
        operation = result.get('operation', 'unknown')
        
        if operation == 'append':
            return f"✓ Appended to '{path}' ({result.get('bytes_added', 0)} bytes added)\n\nDiff:\n{result.get('diff', 'No diff available')}"
        elif operation == 'find_replace':
            changes = result.get('changes', [])
            total = result.get('total_replacements', 0)
            changes_text = "\n".join([f"  • '{c['find']}' → '{c['replace']}' ({c['occurrences']}x)" for c in changes])
            return f"✓ File '{path}' updated with {total} replacement(s)\n\nChanges:\n{changes_text}\n\nDiff:\n{result.get('diff', '')}"
        else:
            return f"✓ File '{path}' completely replaced\n\nDiff:\n{result.get('diff', '')}"
    else:
        return f"✗ Error: {result.get('error', 'Unknown error')}"


def get_file_tools() -> Dict[str, Any]:
    """
    Get all file operation tools for use in agent systems.

    This function returns a dictionary of all file operation tools that
    can be used by LangGraph agents for file-based context engineering.

    Returns:
        Dict[str, Any]: Dictionary mapping tool names to tool instances

    Example:
        >>> tools = get_file_tools()
        >>> print(tools.keys())  # ['read_file', 'write_file', 'edit_file']
    """
    return {
        "read_file": read_file_tool,
        "write_file": write_file_tool,
        "edit_file": edit_file_tool
    }

"""
Assignable tools for the Supervisor Agent system.

This module contains tools that can be dynamically assigned to subagents
based on task requirements. Implements code execution, web search, and
web scraping tools for comprehensive information gathering and processing.
"""

import subprocess
import sys
import traceback
import os
import glob
from pathlib import Path
from typing import Dict, Any, List
from langchain.tools import tool

# API imports with error handling for missing dependencies
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    FirecrawlApp = None


@tool
def execute_code_tool(code: str) -> Dict[str, Any]:
    """
    Execute Python code and return output.
    Automatically captures any files created during execution into the virtual filesystem.
    
    Args:
        code: Python code to execute
        
    Returns:
        dict with success, output, error, and files_created fields
    """
    import json
    from src.core.file_system import VirtualFileSystem
    
    # Get list of existing files before execution
    existing_files = set()
    for pattern in ['**/*.csv', '**/*.txt', '**/*.py', '**/*.json', '**/*.md']:
        existing_files.update(glob.glob(pattern, recursive=True))
    
    code_escaped = json.dumps(code)
    
    # Wrapper that handles both expressions and statements
    wrapper_code = f'''
import sys
from io import StringIO

# Capture stdout
old_stdout = sys.stdout
captured = StringIO()
sys.stdout = captured

try:
    # First try: evaluate as pure expression
    try:
        __result = eval({code_escaped})
        sys.stdout = old_stdout
        if __result is not None:
            print(f"Result: {{__result}}")
    except SyntaxError:
        # Second try: execute as statements, then try to eval last line
        sys.stdout = old_stdout
        
        # Split code into lines
        lines = {code_escaped}.strip().split("\\n")
        
        # Execute all lines
        exec({code_escaped}, globals())
        
        # Try to evaluate the last non-empty line
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    __result = eval(line, globals())
                    if __result is not None:
                        print(f"Result: {{__result}}")
                except:
                    pass
                break
        
        # Print any captured output from the exec
        captured_text = captured.getvalue()
        if captured_text:
            print(captured_text, end='')
            
except Exception as e:
    sys.stdout = old_stdout
    print(f"Error: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', wrapper_code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()  # Run in current directory
        )
        
        # Scan for newly created files
        new_files = set()
        for pattern in ['**/*.csv', '**/*.txt', '**/*.py', '**/*.json', '**/*.md']:
            new_files.update(glob.glob(pattern, recursive=True))
        
        created_files = new_files - existing_files
        
        # Import new files into VirtualFileSystem
        fs = VirtualFileSystem()
        imported_files = []
        
        for filepath in created_files:
            try:
                # Read file content
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Normalize path separators
                vfs_path = filepath.replace('\\', '/')
                
                # Import into VFS
                fs.write_file(vfs_path, content)
                imported_files.append(vfs_path)
                
                # Delete OS file
                os.remove(filepath)
                
            except Exception as e:
                # If file is binary or read fails, skip it
                pass
        
        # Clean up empty directories
        for root, dirs, files in os.walk('.', topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except:
                    pass
        
        success = result.returncode == 0
        response = {
            'success': success,
            'output': result.stdout,
            'error': result.stderr if not success else None
        }
        
        if imported_files:
            response['files_created'] = imported_files
            response['output'] += f"\n\n[Captured {len(imported_files)} file(s) into virtual filesystem: {', '.join(imported_files)}]"
        
        return response
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': 'Code execution timed out after 30 seconds',
            'files_created': []
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'files_created': []
        }


@tool
def search_internet_tool(query: str) -> List[Dict[str, str]]:
    """
    Search the internet for current information using Tavily API.

    This tool performs web searches using the Tavily search engine to find
    current, relevant information from across the internet. It's particularly
    useful for research, fact-checking, and gathering up-to-date information
    that isn't available in the agent's training data.

    Use this tool when you need to:
    - Research current events or recent developments
    - Find factual information or statistics
    - Gather information from multiple sources
    - Verify facts or get updated data
    - Access real-time information not in training data

    Args:
        query: Search query string (e.g., "latest AI developments 2024")

    Returns:
        List of dictionaries, each containing:
        - title: Title of the search result
        - url: URL of the source
        - snippet: Brief excerpt from the content

    Note:
        Requires TAVILY_API_KEY environment variable to be set.
        If API key is missing, returns error message.

    Example:
        >>> results = search_internet_tool("Python async programming")
        >>> print(results[0]['title'])  # First result title
        >>> print(results[0]['url'])    # Source URL
    """
    # Check if Tavily is available and API key is set
    if not TAVILY_AVAILABLE:
        return [{"error": "Tavily package not installed. Install with: pip install tavily-python"}]

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "TAVILY_API_KEY environment variable not set"}]

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Perform search
        response = client.search(query)

        # Format results
        results = []
        for result in response.get('results', []):
            results.append({
                "title": result.get('title', ''),
                "url": result.get('url', ''),
                "snippet": result.get('content', '')[:200] + '...' if len(result.get('content', '')) > 200 else result.get('content', '')
            })

        return results if results else [{"error": "No search results found"}]

    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


@tool
def web_scrape_tool(url: str) -> Dict[str, Any]:
    """
    Extract clean text content from webpages using Firecrawl API.

    This tool scrapes webpages and returns clean, readable text content
    by removing HTML tags, scripts, and other non-content elements. It's
    useful for extracting information from websites that don't have APIs
    or when you need the full content rather than just search snippets.

    Use this tool when you need to:
    - Extract full article content from news sites
    - Get detailed information from documentation pages
    - Access content from websites without APIs
    - Gather comprehensive information from a specific source
    - Process web content for analysis

    Args:
        url: URL of the webpage to scrape (e.g., "https://example.com/article")

    Returns:
        Dict containing:
        - url: The original URL that was scraped
        - content: Clean text content extracted from the page
        - success: Boolean indicating if scraping was successful

    Note:
        Requires FIRECRAWL_API_KEY environment variable to be set.
        If API key is missing, returns error message.

    Example:
        >>> result = web_scrape_tool("https://python.org/")
        >>> print(result['success'])  # True if successful
        >>> print(result['content'][:100])  # First 100 chars of content
    """
    # Check if Firecrawl is available and API key is set
    if not FIRECRAWL_AVAILABLE:
        return {
            "url": url,
            "content": "",
            "success": False,
            "error": "Firecrawl package not installed. Install with: pip install firecrawl-py"
        }

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return {
            "url": url,
            "content": "",
            "success": False,
            "error": "FIRECRAWL_API_KEY environment variable not set"
        }

    try:
        # Initialize Firecrawl app
        app = FirecrawlApp(api_key=api_key)

        # Scrape the webpage - returns a Document object, not a dict
        scrape_result = app.scrape(url)
        
        # The result is a Document object with attributes, not a dictionary
        # Access the content through the markdown or content attribute
        if scrape_result:
            # Try different attribute names depending on Firecrawl version
            content = ""
            
            # Try to get content from various possible attributes
            if hasattr(scrape_result, 'markdown'):
                content = scrape_result.markdown
            elif hasattr(scrape_result, 'content'):
                content = scrape_result.content
            elif hasattr(scrape_result, 'text'):
                content = scrape_result.text
            elif isinstance(scrape_result, dict):
                # Fallback if it's actually a dict
                content = scrape_result.get('markdown', '') or scrape_result.get('content', '')
            
            if content:
                return {
                    "url": url,
                    "content": content,
                    "success": True
                }
            else:
                return {
                    "url": url,
                    "content": "",
                    "success": False,
                    "error": "No content found in scrape result"
                }
        else:
            return {
                "url": url,
                "content": "",
                "success": False,
                "error": "Scraping returned no result"
            }

    except AttributeError as e:
        return {
            "url": url,
            "content": "",
            "success": False,
            "error": f"Scraping failed - attribute error: {str(e)}. The Firecrawl API response format may have changed."
        }
    except Exception as e:
        return {
            "url": url,
            "content": "",
            "success": False,
            "error": f"Scraping failed: {str(e)}"
        }


def test_code_execution() -> Dict[str, Any]:
    """
    Test helper function to verify code execution works correctly.

    This function runs a simple mathematical operation to verify
    that the execute_code_tool is functioning properly.

    Returns:
        Dict: Execution result from running a simple test

    Example:
        >>> result = test_code_execution()
        >>> print(result['success'])  # Should be True
        >>> print(result['output'].strip())  # Should be "42"
    """
    test_code = "print(6 * 7)"
    return execute_code_tool(test_code)


def get_assignable_tools() -> Dict[str, Any]:
    """
    Get all assignable tools for use in agent systems.

    This function returns a dictionary containing all the assignable tools
    that can be dynamically assigned to subagents based on task requirements.
    Each tool is designed for specific types of operations and can be used
    independently or in combination.

    Returns:
        Dict[str, Any]: Dictionary with tool names as keys and tool objects as values:
        - "execute_code": Tool for running Python code
        - "search_internet": Tool for web search using Tavily API
        - "web_scrape": Tool for web scraping using Firecrawl API

    Note:
        Some tools may not be available if their dependencies are not installed
        or if required API keys are not configured. Tools will handle missing
        dependencies gracefully with appropriate error messages.

    Example:
        >>> tools = get_assignable_tools()
        >>> print(tools.keys())  # dict_keys(['execute_code', 'search_internet', 'web_scrape'])
        >>> code_result = tools['execute_code'].invoke({"code": "print(2+2)"})
    """
    return {
        "execute_code": execute_code_tool,
        "search_internet": search_internet_tool,
        "web_scrape": web_scrape_tool
    }

"""
Virtual File System implementation for the Supervisor Agent.

This module provides an in-memory file system simulation that allows agents
to externalize memory and state through file operations, implementing
"context engineering" as described in the Supervisor Agent requirements.
"""

from typing import Dict, List, Union, Any
import difflib


class VirtualFileSystem:
    """
    A singleton virtual file system that simulates file operations in memory.

    This class provides a simple in-memory file system for agents to store,
    read, edit, and manage files as part of their context engineering process.
    All file operations are performed on an internal dictionary that maps
    file paths to their contents.

    The singleton pattern ensures only one file system instance exists,
    providing a shared storage space for all agents and the supervisor.
    """

    _instance: Union['VirtualFileSystem', None] = None
    _files: Dict[str, str] = {}

    def __new__(cls) -> 'VirtualFileSystem':
        """
        Create or return the singleton instance of VirtualFileSystem.

        Returns:
            VirtualFileSystem: The single instance of the virtual file system
        """
        if cls._instance is None:
            cls._instance = super(VirtualFileSystem, cls).__new__(cls)
            cls._instance.files = {}  # Initialize empty file storage
        return cls._instance

    def read_file(self, path: str) -> str:
        """
        Read the content of a file.

        Args:
            path: The path to the file to read

        Returns:
            str: The content of the file

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Invalid file path provided")

        if path not in self.files:
            raise FileNotFoundError(f"File '{path}' not found")

        return self.files[path]

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file, creating it if it doesn't exist or overwriting if it does.

        Args:
            path: The path where to write the file
            content: The content to write to the file

        Returns:
            dict: Dictionary containing 'path', 'bytes_written', and 'status'

        Raises:
            ValueError: If path or content are invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Invalid file path provided")

        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        old_content = self.files.get(path, "")
        was_created = path not in self.files
        self.files[path] = content
        bytes_written = len(content.encode('utf-8'))

        return {
            'path': path,
            'bytes_written': bytes_written,
            'status': 'created' if was_created else 'overwritten'
        }

    def edit_file(self, path: str, edits: Union[List[Dict[str, str]], str], mode: str = "auto") -> Dict[str, Any]:
        """
        Edit an existing file using find/replace operations, append, or whole-file replacement.
        
        Args:
            path: File path to edit
            edits: Either:
                - A string for append or replace operations
                - A list of dicts with "find" and "replace" keys for targeted edits
            mode: Edit mode - "auto", "find_replace", "append", or "replace"
                - auto: Infer from edits type (list=find_replace, string=replace)
                - find_replace: Use find/replace operations
                - append: Add content to end of file
                - replace: Replace entire file content
                
        Returns:
            Dict with success status, path, changes made, and diff
        """
        try:
            if path not in self.files:
                return {
                    "success": False,
                    "error": f"File '{path}' not found",
                    "path": path
                }
            
            original_content = self.files[path]
            
            # Mode: append
            if mode == "append":
                if not isinstance(edits, str):
                    return {
                        "success": False,
                        "error": "Append mode requires string content",
                        "path": path
                    }
                
                # Add newline if file doesn't end with one
                separator = "\n" if original_content and not original_content.endswith("\n") else ""
                new_content = original_content + separator + edits
                self.files[path] = new_content
                
                diff = self._generate_diff(original_content, new_content)
                
                return {
                    "success": True,
                    "path": path,
                    "operation": "append",
                    "bytes_added": len(edits.encode('utf-8')),
                    "diff": diff
                }
            
            # Mode: replace (whole file)
            if mode == "replace" or (mode == "auto" and isinstance(edits, str)):
                self.files[path] = edits
                diff = self._generate_diff(original_content, edits)
                
                return {
                    "success": True,
                    "path": path,
                    "operation": "whole_file_replace",
                    "diff": diff,
                    "bytes_written": len(edits.encode('utf-8')),
                    "original_size": len(original_content.encode('utf-8'))
                }
            
            # Mode: find_replace
            if mode == "find_replace" or (mode == "auto" and isinstance(edits, list)):
                modified_content = original_content
                changes_made = []
                total_replacements = 0
                
                for i, edit in enumerate(edits):
                    if not isinstance(edit, dict):
                        continue
                        
                    if 'find' not in edit or 'replace' not in edit:
                        continue
                    
                    find_str = edit['find']
                    replace_str = edit['replace']
                    
                    count = modified_content.count(find_str)
                    
                    if count > 0:
                        modified_content = modified_content.replace(find_str, replace_str)
                        total_replacements += count
                        changes_made.append({
                            "find": find_str[:50] + "..." if len(find_str) > 50 else find_str,
                            "replace": replace_str[:50] + "..." if len(replace_str) > 50 else replace_str,
                            "occurrences": count
                        })
                
                self.files[path] = modified_content
                diff = self._generate_diff(original_content, modified_content)
                
                return {
                    "success": True,
                    "path": path,
                    "operation": "find_replace",
                    "changes": changes_made,
                    "total_replacements": total_replacements,
                    "diff": diff
                }
            
            return {
                "success": False,
                "error": "Invalid mode or edits format",
                "path": path
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    def _generate_diff(self, original: str, modified: str) -> str:
        """
        Generate a unified diff showing changes between original and modified content.
        
        Args:
            original: Original file content
            modified: Modified file content
            
        Returns:
            Unified diff string
        """
        try:
            diff_lines = difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile='original',
                tofile='modified',
                lineterm=''
            )
            diff_text = ''.join(diff_lines)
            
            # If no differences, return message
            if not diff_text:
                return "No changes detected"
            
            return diff_text
        except Exception as e:
            return f"Error generating diff: {str(e)}"

    def list_files(self) -> List[str]:
        """
        List all file paths in the virtual file system.

        Returns:
            list[str]: A list of all file paths currently stored
        """
        return list(self.files.keys())

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in the virtual file system.

        Args:
            path: The path to check

        Returns:
            bool: True if the file exists, False otherwise

        Raises:
            ValueError: If the path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Invalid file path provided")

        return path in self.files

    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file from the virtual file system.

        Args:
            path: The path of the file to delete

        Returns:
            dict: Dictionary containing 'path' and 'status'

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Invalid file path provided")

        if path not in self.files:
            raise FileNotFoundError(f"File '{path}' not found")

        del self.files[path]
        return {
            'path': path,
            'status': 'deleted'
        }

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get information about a file.

        Args:
            path: The path of the file

        Returns:
            dict: Dictionary containing file information

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Invalid file path provided")

        if path not in self.files:
            raise FileNotFoundError(f"File '{path}' not found")

        content = self.files[path]
        return {
            'path': path,
            'size_bytes': len(content.encode('utf-8')),
            'size_chars': len(content),
            'lines': len(content.splitlines()) if content else 0,
            'exists': True
        }

    def clear_all(self) -> Dict[str, Any]:
        """
        Clear all files from the virtual file system.

        Returns:
            dict: Dictionary containing 'files_cleared' count and 'status'
        """
        files_cleared = len(self.files)
        self.files.clear()
        return {
            'files_cleared': files_cleared,
            'status': 'all_files_cleared'
        }

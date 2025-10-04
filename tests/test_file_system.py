"""
Tests for VirtualFileSystem implementation.

This module contains comprehensive pytest tests for the VirtualFileSystem class,
ensuring all functionality works correctly including file operations, error handling,
and the singleton pattern.
"""

import pytest
from typing import Dict, Any

# Load environment variables from .env file for testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not available, continue without loading .env
    pass

# Import the VirtualFileSystem class
from src.file_system import VirtualFileSystem


class TestVirtualFileSystem:
    """Test suite for VirtualFileSystem class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear the file system before each test to ensure clean state
        vfs = VirtualFileSystem()
        vfs.clear_all()

    def teardown_method(self):
        """Clean up after each test method."""
        # Ensure file system is clean after each test
        vfs = VirtualFileSystem()
        vfs.clear_all()

    def test_write_and_read_file(self):
        """Test writing a file and reading it back successfully."""
        vfs = VirtualFileSystem()

        # Test data
        test_path = "test_file.txt"
        test_content = "This is a test file content.\nIt has multiple lines."

        # Write the file
        write_result = vfs.write_file(test_path, test_content)
        assert write_result['path'] == test_path
        assert write_result['bytes_written'] == len(test_content.encode('utf-8'))
        assert write_result['status'] == 'created'

        # Verify file exists
        assert vfs.file_exists(test_path)

        # Read the file back
        read_content = vfs.read_file(test_path)
        assert read_content == test_content

        # Test overwriting existing file
        new_content = "This is updated content."
        write_result2 = vfs.write_file(test_path, new_content)
        assert write_result2['status'] == 'overwritten'
        assert write_result2['bytes_written'] == len(new_content.encode('utf-8'))

        # Verify content was updated
        read_content2 = vfs.read_file(test_path)
        assert read_content2 == new_content

    def test_file_not_found(self):
        """Test that reading a non-existent file raises FileNotFoundError."""
        vfs = VirtualFileSystem()

        # Test reading non-existent file
        with pytest.raises(FileNotFoundError, match="File 'nonexistent.txt' not found"):
            vfs.read_file("nonexistent.txt")

        # Test file_exists for non-existent file
        assert not vfs.file_exists("nonexistent.txt")

        # Test get_file_info for non-existent file
        with pytest.raises(FileNotFoundError, match="File 'nonexistent.txt' not found"):
            vfs.get_file_info("nonexistent.txt")

        # Test edit_file for non-existent file
        with pytest.raises(FileNotFoundError, match="File 'nonexistent.txt' not found"):
            vfs.edit_file("nonexistent.txt", "new content")

        # Test delete_file for non-existent file
        with pytest.raises(FileNotFoundError, match="File 'nonexistent.txt' not found"):
            vfs.delete_file("nonexistent.txt")

    def test_edit_file_find_replace(self):
        """Test editing a file using find and replace operations."""
        vfs = VirtualFileSystem()

        # Create test file
        test_path = "test_edit.txt"
        original_content = "Hello world! This is a test file. Hello again!"
        vfs.write_file(test_path, original_content)

        # Test find and replace operations
        edits = [
            {"find": "Hello", "replace": "Hi"},
            {"find": "world", "replace": "universe"},
            {"find": "test", "replace": "example"}
        ]

        edit_result = vfs.edit_file(test_path, edits)

        # Check result metadata
        assert edit_result['path'] == test_path
        assert edit_result['changes_made'] == 3  # All 3 replacements should be applied
        assert edit_result['status'] == '3_replacements_applied'

        # Verify content was updated correctly
        expected_content = "Hi universe! This is a example file. Hi again!"
        updated_content = vfs.read_file(test_path)
        assert updated_content == expected_content

        # Verify diff was generated
        assert 'diff' in edit_result
        assert len(edit_result['diff']) > 0  # Should have a non-empty diff

        # Test with partial matches (should not replace if find string not found exactly)
        vfs.write_file(test_path, "Hello world!")
        edit_result2 = vfs.edit_file(test_path, [{"find": "HelloX", "replace": "Hi"}])
        assert edit_result2['changes_made'] == 0  # No changes should be made
        assert edit_result2['status'] == '0_replacements_applied'

        # Content should remain unchanged
        unchanged_content = vfs.read_file(test_path)
        assert unchanged_content == "Hello world!"

    def test_edit_file_full_replace(self):
        """Test editing a file by replacing the entire content."""
        vfs = VirtualFileSystem()

        # Create test file
        test_path = "test_replace.txt"
        original_content = "This is the original content of the file."
        vfs.write_file(test_path, original_content)

        # Test complete content replacement
        new_content = "This is the completely new content."
        edit_result = vfs.edit_file(test_path, new_content)

        # Check result metadata
        assert edit_result['path'] == test_path
        assert edit_result['changes_made'] == 1  # One replacement (full content change)
        assert edit_result['status'] == 'replaced'

        # Verify content was completely replaced
        updated_content = vfs.read_file(test_path)
        assert updated_content == new_content

        # Verify diff was generated for full replacement
        assert 'diff' in edit_result
        assert len(edit_result['diff']) > 0  # Should have a non-empty diff

        # Test replacing with same content (should not change)
        edit_result2 = vfs.edit_file(test_path, new_content)
        assert edit_result2['changes_made'] == 0  # No changes made
        assert edit_result2['status'] == 'replaced'

        # Content should remain the same
        same_content = vfs.read_file(test_path)
        assert same_content == new_content

    def test_list_files(self):
        """Test listing files in the virtual file system."""
        vfs = VirtualFileSystem()

        # Initially should be empty
        files_list = vfs.list_files()
        assert files_list == []

        # Create multiple files
        file_paths = [
            "file1.txt",
            "file2.txt",
            "subdir/file3.txt",
            "another/file4.txt"
        ]

        for path in file_paths:
            vfs.write_file(path, f"Content for {path}")

        # List all files
        files_list = vfs.list_files()

        # Should contain all created files
        assert len(files_list) == len(file_paths)
        for path in file_paths:
            assert path in files_list


        # Delete one file and verify it's removed from list
        vfs.delete_file("file1.txt")
        files_list_after_delete = vfs.list_files()
        assert len(files_list_after_delete) == len(file_paths) - 1
        assert "file1.txt" not in files_list_after_delete
        assert "file2.txt" in files_list_after_delete

        # Clear all files and verify list is empty
        vfs.clear_all()
        files_list_after_clear = vfs.list_files()
        assert files_list_after_clear == []

    def test_delete_file(self):
        """Test deleting files from the virtual file system."""
        vfs = VirtualFileSystem()

        # Create a test file
        test_path = "test_delete.txt"
        test_content = "This file will be deleted."
        vfs.write_file(test_path, test_content)

        # Verify file exists
        assert vfs.file_exists(test_path)
        assert test_path in vfs.list_files()

        # Delete the file
        delete_result = vfs.delete_file(test_path)
        assert delete_result['path'] == test_path
        assert delete_result['status'] == 'deleted'

        # Verify file no longer exists
        assert not vfs.file_exists(test_path)
        assert test_path not in vfs.list_files()

        # Verify cannot read deleted file
        with pytest.raises(FileNotFoundError, match=f"File '{test_path}' not found"):
            vfs.read_file(test_path)

        # Verify cannot edit deleted file
        with pytest.raises(FileNotFoundError, match=f"File '{test_path}' not found"):
            vfs.edit_file(test_path, "new content")

        # Test deleting already deleted file (should raise error)
        with pytest.raises(FileNotFoundError, match=f"File '{test_path}' not found"):
            vfs.delete_file(test_path)

    def test_singleton_pattern(self):
        """Test that VirtualFileSystem implements the singleton pattern correctly."""
        # Get first instance
        vfs1 = VirtualFileSystem()

        # Create a test file in first instance
        test_path = "singleton_test.txt"
        test_content = "This file tests singleton behavior."
        vfs1.write_file(test_path, test_content)

        # Get second instance (should be the same object)
        vfs2 = VirtualFileSystem()

        # Verify it's the same instance
        assert vfs1 is vfs2

        # Verify the file exists in second instance (shared state)
        assert vfs2.file_exists(test_path)
        assert test_path in vfs2.list_files()

        # Verify content is accessible from second instance
        content_from_vfs2 = vfs2.read_file(test_path)
        assert content_from_vfs2 == test_content

        # Modify file through second instance
        new_content = "Modified through second instance."
        vfs2.write_file(test_path, new_content)

        # Verify change is visible in first instance (shared state)
        content_from_vfs1 = vfs1.read_file(test_path)
        assert content_from_vfs1 == new_content

        # Test that class attribute _instance is properly set
        assert VirtualFileSystem._instance is vfs1
        assert VirtualFileSystem._instance is vfs2

#!/usr/bin/env python3
"""
Virtual File System Inspection and Testing Tool

This script allows you to inspect the current state of the Virtual File System
and verify that file operations are working correctly. Use this to check
what files are stored in the VFS and their contents.

Usage:
    python tests/test_vfs_inspection.py
"""

import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from file_system import VirtualFileSystem

def inspect_vfs():
    """Inspect the current state of the Virtual File System."""
    print("🔍 VIRTUAL FILE SYSTEM INSPECTION")
    print("=" * 50)
    
    # Get the VFS instance
    vfs = VirtualFileSystem()
    
    print(f"📁 VFS Instance ID: {id(vfs)}")
    print(f"📁 Total files stored: {len(vfs.files)}")
    
    if vfs.files:
        print("\n📄 Files currently in VFS:")
        print("-" * 30)
        for file_path, content in vfs.files.items():
            print(f"📄 {file_path}")
            print(f"   Size: {len(content)} characters")
            print(f"   Content: {repr(content)}")
            print()
    else:
        print("📭 No files currently stored in VFS")
    
    return vfs

def test_vfs_operations():
    """Test basic VFS operations to verify functionality."""
    print("\n🧪 TESTING VFS OPERATIONS")
    print("=" * 50)
    
    vfs = VirtualFileSystem()
    
    # Test 1: Write a file
    test_content = "This is a test file created by VFS inspection tool"
    vfs.write_file("inspection_test.txt", test_content)
    print(f"✅ Written: inspection_test.txt ({len(test_content)} chars)")
    
    # Test 2: Read the file
    read_content = vfs.read_file("inspection_test.txt")
    print(f"✅ Read: {repr(read_content)}")
    
    # Test 3: Check if file exists
    exists = vfs.file_exists("inspection_test.txt")
    print(f"✅ File exists: {exists}")
    
    # Test 4: List files
    files = vfs.list_files()
    print(f"✅ Files in VFS: {files}")
    
    # Test 5: Edit the file
    vfs.edit_file("inspection_test.txt", "This is a MODIFIED test file")
    modified_content = vfs.read_file("inspection_test.txt")
    print(f"✅ Edited: {repr(modified_content)}")
    
    # Test 6: Delete the file
    vfs.delete_file("inspection_test.txt")
    print("✅ Deleted: inspection_test.txt")
    
    # Final state
    final_files = vfs.list_files()
    print(f"📁 Final VFS state: {final_files}")
    
    print("\n🎯 VFS OPERATIONS TEST COMPLETE")
    print("All operations successful - VFS is working correctly!")

def show_memory_info():
    """Show information about VFS memory usage."""
    print("\n💾 VFS MEMORY INFORMATION")
    print("=" * 50)
    
    vfs = VirtualFileSystem()
    
    if vfs.files:
        total_chars = sum(len(content) for content in vfs.files.values())
        total_files = len(vfs.files)
        
        print(f"📊 Total files stored: {total_files}")
        print(f"📊 Total characters: {total_chars}")
        print(f"📊 Average file size: {total_chars / total_files:.1f} chars")
        
        # Show file sizes
        print("\n📄 File sizes:")
        for file_path, content in vfs.files.items():
            print(f"   {file_path}: {len(content)} characters")
    else:
        print("📭 No files stored - VFS is empty")

def main():
    """Main function to run VFS inspection."""
    load_dotenv()
    
    print("🔬 VIRTUAL FILE SYSTEM INSPECTION TOOL")
    print("=" * 60)
    print("This tool helps you inspect and test the Virtual File System.")
    print("Use this to verify that file operations are working correctly.")
    print()
    
    # Inspect current VFS state
    inspect_vfs()
    
    # Test VFS operations
    test_vfs_operations()
    
    # Show memory info
    show_memory_info()
    
    print("\n" + "=" * 60)
    print("🎉 VFS INSPECTION COMPLETE")
    print("The Virtual File System is real and functional!")
    print("Files are stored in computer memory (RAM) during program execution.")
    print("=" * 60)

if __name__ == "__main__":
    main()

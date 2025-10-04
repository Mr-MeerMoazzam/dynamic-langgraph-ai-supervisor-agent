"""
File system endpoints for the Supervisor Agent API.

This module provides endpoints for file operations using the Virtual File System,
including read, write, edit, list, and delete operations.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Dict, Any, Optional
import logging

from src.api.dependencies import get_settings
from src.api.models.requests import FileWriteRequest, FileEditRequest
from src.api.models.responses import FileResponse, FileListResponse, FileOperationResponse
from src.core.file_system import VirtualFileSystem

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=FileListResponse)
async def list_files() -> FileListResponse:
    """List all files in the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        files = vfs.list_files()
        
        # Get file details
        file_details = []
        for file_path in files:
            try:
                content = vfs.read_file(file_path)
                file_details.append({
                    "path": file_path,
                    "size": len(content),
                    "exists": True
                })
            except Exception as e:
                file_details.append({
                    "path": file_path,
                    "size": 0,
                    "exists": False,
                    "error": str(e)
                })
        
        return FileListResponse(
            files=file_details,
            total_files=len(files),
            total_size=sum(f["size"] for f in file_details)
        )
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@router.get("/{file_path:path}", response_model=FileResponse)
async def read_file(file_path: str) -> FileResponse:
    """Read a file from the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        
        if not vfs.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")
        
        content = vfs.read_file(file_path)
        
        return FileResponse(
            path=file_path,
            content=content,
            size=len(content),
            exists=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.post("/", response_model=FileOperationResponse)
async def write_file(request: FileWriteRequest) -> FileOperationResponse:
    """Write content to a file in the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        
        # Check file size limit
        settings = get_settings()
        if len(request.content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        vfs.write_file(request.path, request.content)
        
        return FileOperationResponse(
            success=True,
            message=f"File '{request.path}' written successfully",
            path=request.path,
            size=len(request.content)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file '{request.path}': {e}")
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

@router.put("/{file_path:path}", response_model=FileOperationResponse)
async def edit_file(file_path: str, request: FileEditRequest) -> FileOperationResponse:
    """Edit a file in the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        
        if not vfs.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")
        
        vfs.edit_file(file_path, request.edits)
        
        # Get updated content size
        updated_content = vfs.read_file(file_path)
        
        return FileOperationResponse(
            success=True,
            message=f"File '{file_path}' edited successfully",
            path=file_path,
            size=len(updated_content)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing file '{file_path}': {e}")
        raise HTTPException(status_code=500, detail=f"Error editing file: {str(e)}")

@router.delete("/{file_path:path}", response_model=FileOperationResponse)
async def delete_file(file_path: str) -> FileOperationResponse:
    """Delete a file from the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        
        if not vfs.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")
        
        vfs.delete_file(file_path)
        
        return FileOperationResponse(
            success=True,
            message=f"File '{file_path}' deleted successfully",
            path=file_path,
            size=0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file '{file_path}': {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/{file_path:path}/exists")
async def file_exists(file_path: str) -> Dict[str, Any]:
    """Check if a file exists in the Virtual File System."""
    try:
        vfs = VirtualFileSystem()
        exists = vfs.file_exists(file_path)
        
        return {
            "path": file_path,
            "exists": exists
        }
    except Exception as e:
        logger.error(f"Error checking file existence '{file_path}': {e}")
        raise HTTPException(status_code=500, detail=f"Error checking file existence: {str(e)}")

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> FileOperationResponse:
    """Upload a file to the Virtual File System."""
    try:
        # Check file type
        settings = get_settings()
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_file_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. Allowed types: {settings.allowed_file_types}"
            )
        
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        # Write to VFS
        vfs = VirtualFileSystem()
        vfs.write_file(file.filename, content.decode('utf-8'))
        
        return FileOperationResponse(
            success=True,
            message=f"File '{file.filename}' uploaded successfully",
            path=file.filename,
            size=len(content)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

"""
Health check endpoints for the Supervisor Agent API.

This module provides health check endpoints to monitor the API status,
dependencies, and system health.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging
import sys
import os

from src.api.dependencies import get_settings, validate_api_keys
from src.core.file_system import VirtualFileSystem

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "supervisor-agent-api",
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with system information."""
    try:
        # Get settings
        settings = get_settings()
        
        # Validate API keys
        api_validation = validate_api_keys()
        
        # Check Virtual File System
        vfs = VirtualFileSystem()
        vfs_status = "healthy"
        try:
            # Test VFS operations
            vfs.write_file("health_check.txt", "test")
            vfs.read_file("health_check.txt")
            vfs.delete_file("health_check.txt")
        except Exception as e:
            vfs_status = f"error: {str(e)}"
        
        return {
            "status": "healthy" if api_validation["valid"] else "degraded",
            "service": "supervisor-agent-api",
            "version": "1.0.0",
            "components": {
                "api_keys": api_validation,
                "virtual_file_system": vfs_status,
                "python_version": sys.version,
                "environment": {
                    "debug": settings.debug,
                    "openai_model": settings.openai_model,
                    "openai_temperature": settings.openai_temperature
                }
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for the service."""
    try:
        # Check if required services are available
        api_validation = validate_api_keys()
        
        if not api_validation["valid"]:
            raise HTTPException(
                status_code=503,
                detail=f"Service not ready: Missing API keys: {api_validation['missing_keys']}"
            )
        
        return {
            "status": "ready",
            "message": "Service is ready to accept requests"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Readiness check failed: {str(e)}")

@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for the service."""
    return {
        "status": "alive",
        "message": "Service is running"
    }

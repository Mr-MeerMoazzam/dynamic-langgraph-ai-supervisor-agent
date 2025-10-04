"""
FastAPI application for the Supervisor Agent system.

This module provides the main FastAPI application with all API endpoints
for agent execution, file system operations, and health checks.
"""

from .main import app

__all__ = ["app"]

#!/usr/bin/env python3
"""
Startup script for the Supervisor Agent FastAPI application.

This script starts the FastAPI server with proper configuration.
"""

import uvicorn
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8002))  # Changed default to 8002
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"🚀 Starting Supervisor Agent API on {host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔍 Health Check: http://{host}:{port}/health")
    
    # Start the server
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info" if not debug else "debug"
    )

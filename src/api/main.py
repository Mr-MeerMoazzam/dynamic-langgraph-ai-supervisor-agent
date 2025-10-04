"""
FastAPI main application for the Supervisor Agent system.

This module creates and configures the FastAPI application with all routes,
middleware, and dependencies for the Supervisor Agent API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

from src.api.routes import agent, files, health
from src.api.dependencies import get_settings
import logging

logger = logging.getLogger(__name__)




# Load environment variables
load_dotenv()

# Configure LangSmith tracing if available
def setup_langsmith_tracing():
    """Setup LangSmith tracing if API key is available."""
    try:
        settings = get_settings()
        # Check for either LANGSMITH_API_KEY or LANGCHAIN_API_KEY
        langsmith_key = settings.langsmith_api_key or settings.langchain_api_key
        
        if langsmith_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = langsmith_key
            if settings.langsmith_project or settings.langchain_project:
                project_name = settings.langsmith_project or settings.langchain_project
                os.environ["LANGCHAIN_PROJECT"] = project_name
            logger.info("✅ LangSmith tracing enabled")
        else:
            logger.info("ℹ️ LangSmith tracing disabled (no API key)")
    except Exception as e:
        logger.warning(f"⚠️ Could not setup LangSmith tracing: {e}")

# Setup LangSmith tracing
setup_langsmith_tracing()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Supervisor Agent API",
    description="API for the LangGraph-based Supervisor Agent system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(files.router, prefix="/files", tags=["files"])

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Supervisor Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "agent": "/agent",
        "files": "/files"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

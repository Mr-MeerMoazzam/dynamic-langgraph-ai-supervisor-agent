"""
Shared dependencies for the FastAPI application.

This module provides common dependencies, settings, and utilities
used across the API endpoints.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    api_title: str = "Supervisor Agent API"
    api_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # OpenAI Settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.1, description="OpenAI temperature")
    
    # External API Settings
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")
    firecrawl_api_key: Optional[str] = Field(default=None, description="Firecrawl API key")
    
    # LangSmith Settings
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    langsmith_project: Optional[str] = Field(default=None, description="LangSmith project name")
    
    # LangChain Settings (these map to LANGCHAIN_* environment variables)
    langchain_api_key: Optional[str] = Field(default=None, description="LangChain API key", alias="LANGCHAIN_API_KEY")
    langchain_tracing_v2: Optional[str] = Field(default=None, description="LangChain tracing v2", alias="LANGCHAIN_TRACING_V2")
    langchain_project: Optional[str] = Field(default=None, description="LangChain project name", alias="LANGCHAIN_PROJECT")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # File System Settings
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Maximum file size in bytes")
    allowed_file_types: list = Field(default=[".txt", ".py", ".json", ".md"], description="Allowed file types")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()

def get_openai_api_key() -> str:
    """Get OpenAI API key from settings."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return settings.openai_api_key

def get_tavily_api_key() -> Optional[str]:
    """Get Tavily API key from settings."""
    settings = get_settings()
    return settings.tavily_api_key

def get_firecrawl_api_key() -> Optional[str]:
    """Get Firecrawl API key from settings."""
    settings = get_settings()
    return settings.firecrawl_api_key

def get_langsmith_api_key() -> Optional[str]:
    """Get LangSmith API key from settings."""
    settings = get_settings()
    return settings.langsmith_api_key

def validate_api_keys() -> dict:
    """Validate that required API keys are present."""
    settings = get_settings()
    missing_keys = []
    
    if not settings.openai_api_key:
        missing_keys.append("OPENAI_API_KEY")
    
    return {
        "valid": len(missing_keys) == 0,
        "missing_keys": missing_keys,
        "available_services": {
            "openai": bool(settings.openai_api_key),
            "tavily": bool(settings.tavily_api_key),
            "firecrawl": bool(settings.firecrawl_api_key),
            "langsmith": bool(settings.langsmith_api_key),
            "langchain": bool(settings.langchain_api_key)
        }
    }

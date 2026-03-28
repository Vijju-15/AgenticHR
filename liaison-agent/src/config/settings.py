"""Configuration settings for Liaison Agent."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os
from pathlib import Path

# Load .env file explicitly
from dotenv import load_dotenv

# Get project root (liaison-agent folder)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"

# Load environment variables
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded .env from: {env_path}")
else:
    print(f"[WARN] No .env file found at: {env_path}")


class Settings(BaseSettings):
    """Application settings."""
    
    # Groq AI
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    @field_validator('groq_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate Groq API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError(
                "GROQ_API_KEY is required! "
                "Please set it in .env file. "
                "Get your key from: https://console.groq.com/keys"
            )
        return v.strip()
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    api_workers: int = 1
    
    # Service URLs
    guide_agent_url: str = "http://localhost:8000"
    orchestrator_agent_url: str = "http://localhost:8001"
    liaison_agent_url: str = "http://localhost:8002"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/liaison.log"
    
    # Environment
    environment: str = "development"

    # API key (optional – if set, all endpoints except /health and /metrics require X-API-Key header)
    api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'


# Initialize settings
try:
    settings = Settings()
    print(f"[OK] Settings loaded successfully")
    print(f"[OK] Groq API Key: {settings.groq_api_key[:20]}... (length: {len(settings.groq_api_key)})")
except Exception as e:
    print(f"[ERROR] Error loading settings: {e}")
    raise

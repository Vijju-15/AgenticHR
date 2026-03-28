"""Configuration settings for Provisioning Agent."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os
from pathlib import Path

# Load .env file explicitly
from dotenv import load_dotenv

# Get project root (provisioning-agent folder)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"

# Load environment variables
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded .env from: {env_path}")
else:
    print(f"[WARN] No .env file found at: {env_path}")


class Settings(BaseSettings):
    """Application settings for Provisioning Agent."""
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # n8n Webhook Base URL
    n8n_webhook_base_url: str = "http://localhost:5678/webhook"
    n8n_api_key: Optional[str] = None

    # MongoDB (for creating login-ready employee records)
    mongodb_url: str = "mongodb://localhost:27017/agentichr"
    company_email_domain: str = "acme.com"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8003
    api_workers: int = 1
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/provisioning.log"
    
    # Environment
    environment: str = "development"
    
    # Retry configuration
    max_retries: int = 1
    retry_delay_seconds: int = 2
    
    # Idempotency
    enable_idempotency_check: bool = True
    
    # Security
    webhook_timeout_seconds: int = 30

    # API key (optional – if set, all endpoints except /health require X-API-Key header)
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
    print(f"[OK] n8n webhook URL: {settings.n8n_webhook_base_url}")
    print(f"[OK] Redis: {settings.redis_host}:{settings.redis_port}")
except Exception as e:
    print(f"[ERROR] Error loading settings: {e}")
    raise

"""Configuration settings for Orchestrator Agent."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Groq AI
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "agentichr"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_workers: int = 2
    
    # Service URLs
    guide_agent_url: str = "http://localhost:8000"
    liaison_agent_url: str = "http://localhost:8002"
    provisioning_agent_url: str = "http://localhost:8003"
    scheduler_agent_url: str = "http://localhost:8004"
    
    # n8n Webhooks
    n8n_base_url: str = "http://localhost:5678"
    n8n_approval_webhook: str = "/webhook/approval"
    n8n_notification_webhook: str = "/webhook/notification"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/orchestrator.log"
    
    # Environment
    environment: str = "development"
    
    # Task Configuration
    max_task_retries: int = 2
    task_timeout_seconds: int = 300

    # Security (optional – if set, all endpoints except /health require X-API-Key header)
    api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

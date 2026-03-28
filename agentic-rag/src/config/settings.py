"""Configuration settings for the HR Assistant Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env file explicitly
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Configuration
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    
    # Vector Store Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "hr_policies"
    qdrant_api_key: Optional[str] = None
    
    # Embedding Model Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_key: str = "development-key"
    
    # Email Configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "hr@company.com"
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Monitoring
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Feature Flags
    enable_conversational_rag: bool = True
    enable_agentic_rag: bool = True
    enable_caching: bool = False
    enable_monitoring: bool = False
    
    # Environment
    environment: str = "development"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/hr_assistant.log"
    
    # Default Leave Balances
    default_leave_balance_casual: int = 15
    default_leave_balance_sick: int = 10
    default_leave_balance_earned: int = 12
    
    # Paths
    @property
    def knowledge_base_path(self) -> Path:
        """Path to the knowledge base directory."""
        return Path("data/knowledge_base")
    
    @property
    def test_cases_path(self) -> Path:
        """Path to the test cases directory."""
        return Path("data/test_cases")
    
    @property
    def logs_path(self) -> Path:
        """Path to the logs directory."""
        return Path("logs")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings."""
    return settings

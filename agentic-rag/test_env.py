import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
print(f".env path: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(dotenv_path=env_path)
print(f"ANTHROPIC_API_KEY from os.getenv: {os.getenv('ANTHROPIC_API_KEY')[:20] if os.getenv('ANTHROPIC_API_KEY') else 'NOT FOUND'}")

from src.config import settings
print(f"ANTHROPIC_API_KEY from settings: {settings.anthropic_api_key[:20] if settings.anthropic_api_key else 'NOT FOUND'}")
print(f"Model: {settings.model_name}")

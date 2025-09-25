from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    GROQ_API_KEY: str
    
    # API Configuration
    APP_NAME: str = "Teranga AI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_KEY_EXPIRE_DAYS: int = 365
    TRIAL_API_KEY_DAYS: int = 30
    
    # Database (Supabase projet-b)
    DATABASE_URL: str
    
    # CORS
    ALLOWED_ORIGINS: list = ["*"]  # À restreindre en production
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_PERIOD: int = 3600  # 1 heure
    
    class Config:
        env_file = None # En production sur Railway
        # env_file = ".env"

settings = Settings()
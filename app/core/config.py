from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    
    # AI
    GEMINI_API_KEY: str
    
    # Google Sheets
    GOOGLE_CREDENTIALS_JSON: Optional[str] = None
    
    # Meta WhatsApp
    WEBHOOK_VERIFY_TOKEN: str
    META_APP_SECRET: Optional[str] = None  # For X-Hub-Signature-256 validation
    
    # Security
    ADMIN_API_KEY: str
    ENCRYPTION_KEY: str
    
    # Input limits
    MAX_MESSAGE_LENGTH: int = 4096  # Reject messages longer than this
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

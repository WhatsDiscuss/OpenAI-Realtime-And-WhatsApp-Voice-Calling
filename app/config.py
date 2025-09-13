"""
Configuration module for WhatsApp Voice + OpenAI Realtime integration.
Loads environment variables and provides configuration values.
"""
import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""
    
    # WhatsApp API Configuration
    WHATSAPP_API_BASE_URL: str = os.getenv("WHATSAPP_API_BASE_URL", "https://graph.facebook.com/v23.0")
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_WEBHOOK_SECRET: str = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_REALTIME_URL: str = os.getenv("OPENAI_REALTIME_URL", "wss://api.openai.com/v1/realtime")
    
    # API Endpoints
    CALL_ANSWER_URL: str = os.getenv("CALL_ANSWER_URL", "https://graph.facebook.com/v23.0/{phone_number_id}/calls")
    
    # Service Configuration
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8080"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CALL_TIMEOUT_SECONDS: int = int(os.getenv("CALL_TIMEOUT_SECONDS", "300"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration values are set."""
        missing = []
        
        if not cls.WHATSAPP_TOKEN:
            missing.append("WHATSAPP_TOKEN")
        if not cls.WHATSAPP_WEBHOOK_SECRET:
            missing.append("WHATSAPP_WEBHOOK_SECRET")
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Global configuration instance
config = Config()
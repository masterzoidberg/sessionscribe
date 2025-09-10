"""
Centralized configuration management using pydantic-settings.
Replaces scattered os.getenv usage and provides secure secret handling.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    # API Keys and Secrets
    openai_api_key: str = ""
    dashboard_provider: str = "openai_api"
    
    # Service Configuration
    asr_port: int = 7035
    redaction_port: int = 7032
    insights_port: int = 7033
    note_builder_port: int = 7034
    
    # Application Settings
    offline_mode: bool = True
    redact_before_send: bool = True
    output_dir: str = ""
    
    # Audio Settings
    sample_rate: int = 44100
    buffer_size_ms: int = 100
    exclusive_mode: bool = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set default output directory if not specified
        if not self.output_dir:
            self.output_dir = os.path.join(
                os.path.expanduser('~'), 
                'Documents', 
                'SessionScribe'
            )
    
    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured (without logging it)."""
        return bool(self.openai_api_key and self.openai_api_key.strip())
    
    def get_redacted_config(self) -> dict:
        """Get configuration dict with secrets redacted for logging."""
        config = self.model_dump()
        
        # Redact sensitive fields
        if config.get('openai_api_key'):
            config['openai_api_key'] = '*' * 8
            
        return config

    class Config:
        env_file = ".env"
        env_prefix = "SS_"
        case_sensitive = False


# Global settings instance
settings = AppSettings()
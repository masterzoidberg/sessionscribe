"""
SessionScribe Service Configuration
Centralized configuration for all services
"""

import os
from typing import Dict, Any

class ServiceConfig:
    # Service ports
    ASR_PORT = int(os.getenv('SS_ASR_PORT', '7031'))
    REDACTION_PORT = int(os.getenv('SS_REDACTION_PORT', '7032'))
    INSIGHTS_PORT = int(os.getenv('SS_INSIGHTS_PORT', '7033'))
    NOTE_BUILDER_PORT = int(os.getenv('SS_NOTE_BUILDER_PORT', '7034'))
    
    # Service hosts
    HOST = os.getenv('SS_HOST', '127.0.0.1')
    
    # Service URLs
    ASR_URL = f"http://{HOST}:{ASR_PORT}"
    REDACTION_URL = f"http://{HOST}:{REDACTION_PORT}"
    INSIGHTS_URL = f"http://{HOST}:{INSIGHTS_PORT}"
    NOTE_BUILDER_URL = f"http://{HOST}:{NOTE_BUILDER_PORT}"
    
    # Application settings
    OFFLINE_MODE = os.getenv('SS_OFFLINE', 'true').lower() == 'true'
    REDACT_BEFORE_SEND = os.getenv('SS_REDACT_BEFORE_SEND', 'true').lower() == 'true'
    OUTPUT_DIR = os.getenv('SS_OUTPUT_DIR', os.path.join(os.path.expanduser('~'), 'Documents', 'SessionScribe'))
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    NOTE_MODEL = os.getenv('SS_NOTE_MODEL', 'gpt-4o-mini')
    NOTE_TEMPERATURE = float(os.getenv('SS_NOTE_TEMPERATURE', '0.2'))
    
    @classmethod
    def get_service_config(cls) -> Dict[str, Any]:
        """Get complete service configuration"""
        return {
            'ports': {
                'asr': cls.ASR_PORT,
                'redaction': cls.REDACTION_PORT,
                'insights': cls.INSIGHTS_PORT,
                'note_builder': cls.NOTE_BUILDER_PORT
            },
            'urls': {
                'asr': cls.ASR_URL,
                'redaction': cls.REDACTION_URL,
                'insights': cls.INSIGHTS_URL,
                'note_builder': cls.NOTE_BUILDER_URL
            },
            'settings': {
                'offline_mode': cls.OFFLINE_MODE,
                'redact_before_send': cls.REDACT_BEFORE_SEND,
                'output_dir': cls.OUTPUT_DIR
            },
            'openai': {
                'api_key': cls.OPENAI_API_KEY,
                'base_url': cls.OPENAI_BASE_URL,
                'model': cls.NOTE_MODEL,
                'temperature': cls.NOTE_TEMPERATURE
            }
        }

    @classmethod
    def validate_config(cls) -> bool:
        """Validate essential configuration"""
        if not os.path.exists(cls.OUTPUT_DIR):
            try:
                os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
            except Exception as e:
                print(f"Error creating output directory: {e}")
                return False
        
        if not cls.OFFLINE_MODE and not cls.OPENAI_API_KEY:
            print("Warning: Online mode enabled but no OpenAI API key found")
            
        return True
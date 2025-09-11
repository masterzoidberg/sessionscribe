"""
Windows Credential Manager integration for SessionScribe services.
"""

import keyring
import secrets
import string
from typing import Optional, Dict
import logging

SERVICE_NAME = "SessionScribe"

logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages secure credential storage via Windows Credential Manager."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.service_name = SERVICE_NAME
            self._initialized = True
    
    def get_credential(self, key: str) -> Optional[str]:
        """Retrieve a credential from Windows Credential Manager."""
        try:
            return keyring.get_password(self.service_name, key)
        except Exception as e:
            logger.error(f"Failed to retrieve credential '{key}': {e}")
            return None
    
    def set_credential(self, key: str, value: str) -> bool:
        """Store a credential in Windows Credential Manager."""
        try:
            keyring.set_password(self.service_name, key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to store credential '{key}': {e}")
            return False
    
    def delete_credential(self, key: str) -> bool:
        """Delete a credential from Windows Credential Manager."""
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"Credential '{key}' not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Failed to delete credential '{key}': {e}")
            return False
    
    def get_all_credentials(self) -> Dict[str, Optional[str]]:
        """Retrieve all SessionScribe credentials."""
        credentials = {}
        keys = [
            'openai_api_key',
            'jwt_signing_key', 
            'encryption_key'
        ]
        
        for key in keys:
            credentials[key] = self.get_credential(key)
        
        return credentials
    
    def generate_secure_key(self, length: int = 64) -> str:
        """Generate a cryptographically secure random key."""
        alphabet = string.ascii_letters + string.digits + '+/'
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def initialize_default_credentials(self) -> bool:
        """Initialize default credentials if they don't exist."""
        try:
            # Check if JWT signing key exists
            if not self.get_credential('jwt_signing_key'):
                jwt_key = self.generate_secure_key()
                if not self.set_credential('jwt_signing_key', jwt_key):
                    return False
                logger.info("Generated new JWT signing key")
            
            # Check if encryption key exists  
            if not self.get_credential('encryption_key'):
                enc_key = self.generate_secure_key()
                if not self.set_credential('encryption_key', enc_key):
                    return False
                logger.info("Generated new encryption key")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize default credentials: {e}")
            return False
    
    def validate_credentials(self) -> Dict[str, bool]:
        """Validate that required credentials are present."""
        validation = {}
        required_keys = ['jwt_signing_key', 'encryption_key']
        
        for key in required_keys:
            credential = self.get_credential(key)
            validation[key] = credential is not None and len(credential) >= 32
        
        return validation


# Global instance
credential_manager = CredentialManager()
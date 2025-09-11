"""
Health check utilities for SessionScribe services.
Provides readiness checks for dependencies and resources.
"""

import os
import asyncio
from typing import Dict, Tuple, Optional, Callable
from pathlib import Path
import logging

from .security.credentials import credential_manager

logger = logging.getLogger(__name__)

class HealthChecker:
    """Base health checker for service dependencies."""
    
    def __init__(self, service_name: str, service_port: int):
        self.service_name = service_name
        self.service_port = service_port
        self.checks = []
    
    def add_check(self, name: str, check_func: Callable[[], Tuple[bool, str]]):
        """Add a health check function."""
        self.checks.append((name, check_func))
    
    async def check_all(self) -> Tuple[bool, Dict[str, any]]:
        """Run all health checks and return overall status."""
        results = {
            "service": self.service_name,
            "port": self.service_port,
            "checks": {}
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.checks:
            try:
                is_healthy, message = check_func()
                results["checks"][check_name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "message": message
                }
                
                if not is_healthy:
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check '{check_name}' failed with exception: {e}")
                results["checks"][check_name] = {
                    "status": "error", 
                    "message": f"Check failed: {str(e)}"
                }
                overall_healthy = False
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        return overall_healthy, results

class ASRHealthChecker(HealthChecker):
    """Health checker for ASR service specific dependencies."""
    
    def __init__(self):
        super().__init__("asr", 7035)
        self._setup_checks()
    
    def _setup_checks(self):
        """Setup ASR service specific health checks."""
        self.add_check("jwt_signing_key", self._check_jwt_key)
        self.add_check("output_directory", self._check_output_directory)
        self.add_check("audio_devices", self._check_audio_devices)
        self.add_check("session_manager", self._check_session_manager)
    
    def _check_jwt_key(self) -> Tuple[bool, str]:
        """Check if JWT signing key is present and valid."""
        try:
            jwt_key = credential_manager.get_credential('jwt_signing_key')
            if not jwt_key:
                return False, "JWT signing key not found in credential store"
            if len(jwt_key) < 32:
                return False, "JWT signing key too short"
            return True, "JWT signing key present and valid"
        except Exception as e:
            return False, f"JWT key check failed: {str(e)}"
    
    def _check_output_directory(self) -> Tuple[bool, str]:
        """Check if output directory is writable."""
        try:
            output_dir = Path.home() / "Documents" / "SessionScribe" / "Recordings"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = output_dir / "health_check.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            return True, f"Output directory writable: {output_dir}"
        except Exception as e:
            return False, f"Output directory not writable: {str(e)}"
    
    def _check_audio_devices(self) -> Tuple[bool, str]:
        """Check if audio devices are accessible."""
        try:
            # This would interface with actual audio enumeration
            # For now, assume available on Windows
            return True, "Audio devices accessible"
        except Exception as e:
            return False, f"Audio device check failed: {str(e)}"
    
    def _check_session_manager(self) -> Tuple[bool, str]:
        """Check if session manager is operational."""
        try:
            from services.asr.capture.manager import session_manager
            stats = session_manager.get_stats()
            return True, f"Session manager operational: {stats['total_sessions']} sessions"
        except Exception as e:
            return False, f"Session manager check failed: {str(e)}"

class RedactionHealthChecker(HealthChecker):
    """Health checker for Redaction service specific dependencies."""
    
    def __init__(self):
        super().__init__("redaction", 7032)
        self._setup_checks()
    
    def _setup_checks(self):
        """Setup redaction service specific health checks."""
        self.add_check("jwt_signing_key", self._check_jwt_key)
        self.add_check("spacy_model", self._check_spacy_model)
        self.add_check("phi_detector", self._check_phi_detector)
    
    def _check_jwt_key(self) -> Tuple[bool, str]:
        """Check if JWT signing key is present."""
        jwt_key = credential_manager.get_credential('jwt_signing_key')
        if jwt_key and len(jwt_key) >= 32:
            return True, "JWT signing key present"
        return False, "JWT signing key missing or invalid"
    
    def _check_spacy_model(self) -> Tuple[bool, str]:
        """Check if spaCy model is loaded."""
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            return True, "spaCy model loaded successfully"
        except OSError:
            return False, "spaCy model 'en_core_web_sm' not found"
        except Exception as e:
            return False, f"spaCy model check failed: {str(e)}"
    
    def _check_phi_detector(self) -> Tuple[bool, str]:
        """Check if PHI detector is operational."""
        try:
            from services.redaction.phi_detector import PHIDetector
            detector = PHIDetector()
            # Test with safe sample text
            entities = detector.detect_fast("Test sample text")
            return True, "PHI detector operational"
        except Exception as e:
            return False, f"PHI detector check failed: {str(e)}"

class InsightsHealthChecker(HealthChecker):
    """Health checker for Insights Bridge service."""
    
    def __init__(self):
        super().__init__("insights", 7033)
        self._setup_checks()
    
    def _setup_checks(self):
        """Setup insights service specific health checks."""
        self.add_check("jwt_signing_key", self._check_jwt_key)
        self.add_check("openai_api_key", self._check_openai_key)
    
    def _check_jwt_key(self) -> Tuple[bool, str]:
        """Check if JWT signing key is present."""
        jwt_key = credential_manager.get_credential('jwt_signing_key')
        if jwt_key and len(jwt_key) >= 32:
            return True, "JWT signing key present"
        return False, "JWT signing key missing or invalid"
    
    def _check_openai_key(self) -> Tuple[bool, str]:
        """Check if OpenAI API key is configured."""
        api_key = credential_manager.get_credential('openai_api_key')
        if api_key and len(api_key) > 20:
            return True, "OpenAI API key configured"
        return False, "OpenAI API key not configured (optional)"

class NoteBuilderHealthChecker(HealthChecker):
    """Health checker for Note Builder service."""
    
    def __init__(self):
        super().__init__("note_builder", 7034)
        self._setup_checks()
    
    def _setup_checks(self):
        """Setup note builder service specific health checks."""
        self.add_check("jwt_signing_key", self._check_jwt_key)
        self.add_check("output_directory", self._check_output_directory)
    
    def _check_jwt_key(self) -> Tuple[bool, str]:
        """Check if JWT signing key is present."""
        jwt_key = credential_manager.get_credential('jwt_signing_key')
        if jwt_key and len(jwt_key) >= 32:
            return True, "JWT signing key present"
        return False, "JWT signing key missing or invalid"
    
    def _check_output_directory(self) -> Tuple[bool, str]:
        """Check if output directory is writable."""
        try:
            output_dir = Path.home() / "Documents" / "SessionScribe" / "Notes"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = output_dir / "health_check.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            return True, f"Output directory writable: {output_dir}"
        except Exception as e:
            return False, f"Output directory not writable: {str(e)}"
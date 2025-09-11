"""
Structured JSON logging configuration for SessionScribe services.
Ensures no PHI/transcript content in logs, only metadata and metrics.
"""

import logging
import json
import sys
import time
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for request tracing
session_context: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
trace_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)

class JSONFormatter(logging.Formatter):
    """JSON formatter that outputs structured logs with no PHI content."""
    
    def __init__(self, service_name: str, service_port: int):
        super().__init__()
        self.service_name = service_name
        self.service_port = service_port
        self.hostname = "localhost"  # For desktop app
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname.lower(),
            "service": self.service_name,
            "port": self.service_port,
            "hostname": self.hostname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # Add context if available
        session_id = session_context.get()
        if session_id:
            log_entry["session_id"] = session_id
        
        trace_id = trace_context.get()
        if trace_id:
            log_entry["trace_id"] = trace_id
        
        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            # Only allow safe fields - no PHI content
            safe_fields = ['request_id', 'endpoint', 'method', 'status_code', 
                          'duration_ms', 'chunk_count', 'buffer_size', 'sample_rate',
                          'channel', 'audio_format', 'device_id', 'error_code']
            
            for field, value in record.extra_fields.items():
                if field in safe_fields:
                    log_entry[field] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add stack info if present
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))

class StructuredLogger:
    """Wrapper for structured logging with context management."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _log(self, level: int, msg: str, **extra_fields):
        """Log with extra fields, ensuring no PHI content."""
        # Filter out any potential PHI fields
        safe_extra = {}
        unsafe_keywords = ['transcript', 'text', 'content', 'audio_data', 'speech',
                          'utterance', 'phrase', 'word', 'sentence']
        
        for key, value in extra_fields.items():
            # Skip fields that might contain PHI
            if any(keyword in key.lower() for keyword in unsafe_keywords):
                continue
            # Only log metadata, not content
            if isinstance(value, str) and len(value) > 100:
                continue  # Skip long strings that might be content
            safe_extra[key] = value
        
        # Create log record with extra fields
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, msg, (), None
        )
        if safe_extra:
            record.extra_fields = safe_extra
        
        self.logger.handle(record)
    
    def debug(self, msg: str, **extra_fields):
        self._log(logging.DEBUG, msg, **extra_fields)
    
    def info(self, msg: str, **extra_fields):
        self._log(logging.INFO, msg, **extra_fields)
    
    def warning(self, msg: str, **extra_fields):
        self._log(logging.WARNING, msg, **extra_fields)
    
    def error(self, msg: str, **extra_fields):
        self._log(logging.ERROR, msg, **extra_fields)
    
    def critical(self, msg: str, **extra_fields):
        self._log(logging.CRITICAL, msg, **extra_fields)

def setup_structured_logging(service_name: str, port: int, level: str = "INFO") -> StructuredLogger:
    """Setup structured JSON logging for a service."""
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name, port))
    
    # Add handler
    logger.addHandler(handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return StructuredLogger(logger)

def set_session_context(session_id: str):
    """Set session ID for current context."""
    session_context.set(session_id)

def set_trace_context(trace_id: Optional[str] = None):
    """Set trace ID for current context."""
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    trace_context.set(trace_id)

def clear_context():
    """Clear logging context."""
    session_context.set(None)
    trace_context.set(None)

def get_session_context() -> Optional[str]:
    """Get current session context."""
    return session_context.get()

def get_trace_context() -> Optional[str]:
    """Get current trace context."""
    return trace_context.get()

# Middleware function for FastAPI
def create_logging_middleware(logger: StructuredLogger):
    """Create FastAPI middleware for request logging."""
    
    async def logging_middleware(request, call_next):
        # Set trace context
        trace_id = str(uuid.uuid4())
        set_trace_context(trace_id)
        
        # Extract session ID from headers or query params
        session_id = request.headers.get('X-Session-ID')
        if not session_id and hasattr(request, 'query_params'):
            session_id = request.query_params.get('session_id')
        
        if session_id:
            set_session_context(session_id)
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log request completion
            duration = (time.time() - start_time) * 1000
            logger.info("Request completed",
                       endpoint=str(request.url.path),
                       method=request.method,
                       status_code=response.status_code,
                       duration_ms=round(duration, 2))
            
            return response
            
        except Exception as e:
            # Log request error
            duration = (time.time() - start_time) * 1000
            logger.error(f"Request failed: {str(e)}",
                        endpoint=str(request.url.path),
                        method=request.method,
                        duration_ms=round(duration, 2),
                        error_type=type(e).__name__)
            raise
        finally:
            # Clear context
            clear_context()
    
    return logging_middleware
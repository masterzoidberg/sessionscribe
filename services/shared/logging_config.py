"""
Structured logging configuration using structlog for all FastAPI services.
Provides JSON logging with consistent fields across services.
"""

import structlog
import logging
import sys
import os
from typing import Any


def configure_logging(service_name: str, port: int) -> structlog.BoundLogger:
    """
    Configure structured logging for a service.
    
    Args:
        service_name: Name of the service (e.g., "asr", "redaction")
        port: Port the service runs on
    
    Returns:
        Configured logger instance
    """
    
    # Create logs directory
    log_dir = "scripts/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Create service-specific logger
    logger = structlog.get_logger(service=service_name, port=port)
    
    # Add file handler for service logs
    file_handler = logging.FileHandler(f"{log_dir}/{service_name}.log")
    file_handler.setLevel(logging.INFO)
    
    # Configure root logger to use the file handler too
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    return logger


def get_request_logger(base_logger: structlog.BoundLogger, request_id: str = None) -> structlog.BoundLogger:
    """
    Get a request-specific logger with request_id bound.
    
    Args:
        base_logger: Base service logger
        request_id: Optional request ID
        
    Returns:
        Logger with request context
    """
    if request_id:
        return base_logger.bind(request_id=request_id)
    return base_logger
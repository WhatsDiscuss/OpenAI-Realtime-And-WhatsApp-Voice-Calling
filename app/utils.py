"""
Utility functions for logging and common helpers.
"""
import logging
import sys
from typing import Any, Dict


def setup_logging(level: str = "INFO") -> None:
    """Setup structured logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter for structured logging
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def log_request_info(method: str, path: str, headers: Dict[str, Any]) -> None:
    """Log incoming request information."""
    logger = logging.getLogger(__name__)
    logger.info(f"Incoming {method} request to {path}")
    logger.debug(f"Request headers: {dict(headers)}")


def log_webhook_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """Log webhook event details."""
    logger = logging.getLogger(__name__)
    logger.info(f"Webhook event received: {event_type}")
    logger.debug(f"Event data: {event_data}")


def log_call_session(call_id: str, action: str, details: str = "") -> None:
    """Log call session events."""
    logger = logging.getLogger(__name__)
    message = f"Call {call_id}: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)


def log_openai_event(event_type: str, details: str = "") -> None:
    """Log OpenAI Realtime API events."""
    logger = logging.getLogger(__name__)
    message = f"OpenAI Realtime: {event_type}"
    if details:
        message += f" - {details}"
    logger.info(message)


def log_webrtc_event(call_id: str, event: str, details: str = "") -> None:
    """Log WebRTC adapter events."""
    logger = logging.getLogger(__name__)
    message = f"WebRTC [{call_id}]: {event}"
    if details:
        message += f" - {details}"
    logger.info(message)
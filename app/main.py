"""
Main HTTP server for WhatsApp Voice + OpenAI Realtime integration.
Provides webhook endpoint and health check using standard library.
"""
import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
import threading
from typing import Dict, Any, Optional

from .config import config
from .webhook_handler import webhook_handler
from .call_session import call_session_manager
from .utils import setup_logging, log_request_info


class AsyncHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server with threading support for async operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_reuse_address = True


class WebhookHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook and health endpoints."""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)
        
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        self.logger.info(f"{self.address_string()} - {format % args}")
        
    def do_GET(self) -> None:
        """Handle GET requests (health check)."""
        parsed_path = urlparse(self.path)
        
        log_request_info("GET", parsed_path.path, self.headers)
        
        if parsed_path.path == "/health":
            self._handle_health_check()
        else:
            self._send_response(404, {"error": "Not found"})
            
    def do_POST(self) -> None:
        """Handle POST requests (webhook)."""
        parsed_path = urlparse(self.path)
        
        log_request_info("POST", parsed_path.path, self.headers)
        
        if parsed_path.path == "/webhook":
            self._handle_webhook()
        else:
            self._send_response(404, {"error": "Not found"})
            
    def _handle_health_check(self) -> None:
        """Handle health check endpoint."""
        active_calls = call_session_manager.get_active_call_count()
        
        health_data = {
            "status": "healthy",
            "service": "whatsapp-openai-realtime",
            "active_calls": active_calls,
            "version": "1.0.0"
        }
        
        self._send_response(200, health_data)
        
    def _handle_webhook(self) -> None:
        """Handle WhatsApp webhook endpoint."""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_response(400, {"error": "Empty request body"})
                return
                
            body = self.rfile.read(content_length)
            
            # Convert headers to dict
            headers = dict(self.headers)
            
            # Process webhook in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                status_code, response_data = loop.run_until_complete(
                    webhook_handler.process_webhook(headers, body)
                )
                self._send_response(status_code, response_data)
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            self._send_response(500, {"error": "Internal server error"})
            
    def _send_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send JSON response."""
        response_body = json.dumps(data, indent=2).encode('utf-8')
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        self.wfile.write(response_body)
        
    def do_OPTIONS(self) -> None:
        """Handle preflight OPTIONS requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()


class WhatsAppServer:
    """Main server class for the WhatsApp integration."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server: Optional[AsyncHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        
    def start(self) -> None:
        """Start the HTTP server."""
        try:
            # Validate configuration
            config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            return
            
        server_address = ('', config.SERVICE_PORT)
        self.server = AsyncHTTPServer(server_address, WebhookHTTPHandler)
        
        self.logger.info(f"Starting WhatsApp-OpenAI server on port {config.SERVICE_PORT}")
        self.logger.info(f"Health check available at: http://localhost:{config.SERVICE_PORT}/health")
        self.logger.info(f"Webhook endpoint available at: http://localhost:{config.SERVICE_PORT}/webhook")
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()
            
    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.logger.info("Stopping server...")
            self.server.shutdown()
            self.server.server_close()
            
        # Clean up active call sessions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(call_session_manager.end_all_calls())
        finally:
            loop.close()
            
        self.logger.info("Server stopped")


def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging(config.LOG_LEVEL)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting WhatsApp Voice + OpenAI Realtime Integration")
    
    # Create and start server
    server = WhatsAppServer()
    server.start()


if __name__ == "__main__":
    main()
"""
WhatsApp webhook handler for processing incoming webhook events.
Handles call initiation events and triggers the call session flow.
"""
import json
import logging
from typing import Dict, Any, Tuple, Optional

from .config import config
from .call_session import call_session_manager
from .utils import log_webhook_event, log_call_session


class WebhookHandler:
    """Handles WhatsApp webhook events."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_webhook_token(self, auth_header: Optional[str]) -> bool:
        """
        Validate the webhook authentication token.
        
        Args:
            auth_header: Authorization header value
            
        Returns:
            True if token is valid, False otherwise
        """
        if not auth_header:
            return False
            
        # Extract token from "Bearer <token>" format
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token == config.WHATSAPP_WEBHOOK_SECRET
            
        # Direct token comparison for testing
        return auth_header == config.WHATSAPP_WEBHOOK_SECRET
        
    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Parse webhook payload and extract event information.
        
        Args:
            payload: Webhook JSON payload
            
        Returns:
            Tuple of (event_type, event_data) or (None, None) if not a call event
        """
        try:
            if payload.get("object") != "whatsapp_business_account":
                return "unknown", None
                
            entries = payload.get("entry", [])
            if not entries:
                return "no_entries", None
                
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    
                    # Check for call initiation event
                    if "call_id" in value and "sdp" in value:
                        event_type = value.get("event", "call.initiated")
                        
                        call_data = {
                            "call_id": value["call_id"],
                            "sdp": value["sdp"],
                            "event": event_type,
                            "phone_number_id": value.get("phone_number_id", "mock_phone_id"),
                            "from": value.get("from", "unknown"),
                            "timestamp": value.get("timestamp")
                        }
                        
                        return "call.initiated", call_data
                        
                    # Handle other webhook events
                    elif "messages" in value:
                        return "message", value
                    elif "statuses" in value:
                        return "status", value
                        
            return "other", payload
            
        except Exception as e:
            self.logger.error(f"Error parsing webhook payload: {e}")
            return "error", {"error": str(e)}
            
    async def handle_webhook_event(self, event_type: str, event_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Handle a parsed webhook event.
        
        Args:
            event_type: Type of event (call.initiated, message, etc.)
            event_data: Event data dictionary
            
        Returns:
            Response data for the webhook
        """
        log_webhook_event(event_type, event_data or {})
        
        if event_type == "call.initiated" and event_data:
            return await self._handle_call_initiation(event_data)
        elif event_type == "message":
            return await self._handle_message_event(event_data or {})
        elif event_type == "status":
            return await self._handle_status_event(event_data or {})
        else:
            return await self._handle_other_event(event_type, event_data or {})
            
    async def _handle_call_initiation(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call initiation event."""
        call_id = call_data["call_id"]
        offer_sdp = call_data["sdp"]
        phone_number_id = call_data.get("phone_number_id", "mock_phone_id")
        
        log_call_session(call_id, "webhook_received", f"From: {call_data.get('from', 'unknown')}")
        
        try:
            # Start the call session asynchronously
            await call_session_manager.handle_new_call(
                call_id=call_id,
                offer_sdp=offer_sdp,
                phone_number_id=phone_number_id
            )
            
            log_call_session(call_id, "webhook_processed", "Call session initiated")
            
            return {
                "status": "success",
                "message": "Call initiation processed",
                "call_id": call_id
            }
            
        except Exception as e:
            self.logger.error(f"Error handling call initiation for {call_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to process call: {str(e)}",
                "call_id": call_id
            }
            
    async def _handle_message_event(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message webhook event."""
        self.logger.info("Received message webhook event")
        return {"status": "acknowledged", "type": "message"}
        
    async def _handle_status_event(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status webhook event.""" 
        self.logger.info("Received status webhook event")
        return {"status": "acknowledged", "type": "status"}
        
    async def _handle_other_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle other webhook events."""
        self.logger.info(f"Received {event_type} webhook event")
        return {"status": "acknowledged", "type": event_type}
        
    async def process_webhook(self, headers: Dict[str, str], body: bytes) -> Tuple[int, Dict[str, Any]]:
        """
        Process complete webhook request.
        
        Args:
            headers: Request headers
            body: Request body bytes
            
        Returns:
            Tuple of (status_code, response_data)
        """
        try:
            # Validate authentication
            auth_header = headers.get("Authorization") or headers.get("authorization")
            if not self.validate_webhook_token(auth_header):
                self.logger.warning("Invalid webhook authentication token")
                return 401, {"error": "Unauthorized"}
                
            # Parse JSON payload
            try:
                payload = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.logger.error(f"Invalid JSON payload: {e}")
                return 400, {"error": "Invalid JSON payload"}
                
            # Parse webhook event
            event_type, event_data = self.parse_webhook_payload(payload)
            
            # Handle the event
            response_data = await self.handle_webhook_event(event_type, event_data)
            
            return 200, response_data
            
        except Exception as e:
            self.logger.error(f"Unexpected error processing webhook: {e}")
            return 500, {"error": "Internal server error"}


# Global webhook handler instance
webhook_handler = WebhookHandler()
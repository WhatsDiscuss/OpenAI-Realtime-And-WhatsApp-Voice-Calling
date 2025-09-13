"""
Tests for WhatsApp webhook handler functionality.
"""
import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.webhook_handler import WebhookHandler
from app.call_session import CallSessionManager


class TestWebhookHandler:
    """Test cases for WebhookHandler class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.handler = WebhookHandler()
        
    def test_validate_webhook_token_with_bearer(self):
        """Test webhook token validation with Bearer format."""
        # Mock config
        with patch('app.webhook_handler.config.WHATSAPP_WEBHOOK_SECRET', 'test_secret'):
            assert self.handler.validate_webhook_token("Bearer test_secret") is True
            assert self.handler.validate_webhook_token("Bearer wrong_secret") is False
            
    def test_validate_webhook_token_direct(self):
        """Test webhook token validation with direct token."""
        with patch('app.webhook_handler.config.WHATSAPP_WEBHOOK_SECRET', 'test_secret'):
            assert self.handler.validate_webhook_token("test_secret") is True
            assert self.handler.validate_webhook_token("wrong_secret") is False
            assert self.handler.validate_webhook_token(None) is False
            
    def test_parse_webhook_payload_call_initiated(self):
        """Test parsing call initiation webhook payload."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "call_id": "test-call-123",
                        "sdp": "v=0\no=- 123 2 IN IP4 127.0.0.1",
                        "event": "call.initiated",
                        "phone_number_id": "phone123",
                        "from": "+1234567890",
                        "timestamp": "1634567890"
                    }
                }]
            }]
        }
        
        event_type, event_data = self.handler.parse_webhook_payload(payload)
        
        assert event_type == "call.initiated"
        assert event_data is not None
        assert event_data["call_id"] == "test-call-123"
        assert event_data["sdp"] == "v=0\no=- 123 2 IN IP4 127.0.0.1"
        assert event_data["phone_number_id"] == "phone123"
        assert event_data["from"] == "+1234567890"
        
    def test_parse_webhook_payload_message(self):
        """Test parsing message webhook payload."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"id": "msg123", "text": {"body": "Hello"}}]
                    }
                }]
            }]
        }
        
        event_type, event_data = self.handler.parse_webhook_payload(payload)
        
        assert event_type == "message"
        assert event_data is not None
        assert "messages" in event_data
        
    def test_parse_webhook_payload_invalid(self):
        """Test parsing invalid webhook payload."""
        payload = {"invalid": "payload"}
        
        event_type, event_data = self.handler.parse_webhook_payload(payload)
        
        assert event_type == "unknown"
        assert event_data is None
        
    @pytest.mark.asyncio
    async def test_handle_call_initiation(self):
        """Test handling call initiation event."""
        call_data = {
            "call_id": "test-call-456",
            "sdp": "mock-sdp-offer",
            "phone_number_id": "phone456",
            "from": "+1234567890"
        }
        
        # Mock the call session manager
        with patch('app.webhook_handler.call_session_manager') as mock_manager:
            mock_manager.handle_new_call = AsyncMock()
            
            response = await self.handler._handle_call_initiation(call_data)
            
            # Verify call session manager was called
            mock_manager.handle_new_call.assert_called_once_with(
                call_id="test-call-456",
                offer_sdp="mock-sdp-offer",
                phone_number_id="phone456"
            )
            
            # Verify response
            assert response["status"] == "success"
            assert response["call_id"] == "test-call-456"
            
    @pytest.mark.asyncio
    async def test_handle_call_initiation_error(self):
        """Test handling call initiation with error."""
        call_data = {
            "call_id": "test-call-error",
            "sdp": "mock-sdp-offer",
            "phone_number_id": "phone_error"
        }
        
        # Mock the call session manager to raise exception
        with patch('app.webhook_handler.call_session_manager') as mock_manager:
            mock_manager.handle_new_call = AsyncMock(side_effect=Exception("Test error"))
            
            response = await self.handler._handle_call_initiation(call_data)
            
            # Verify error response
            assert response["status"] == "error"
            assert "Test error" in response["message"]
            assert response["call_id"] == "test-call-error"
            
    @pytest.mark.asyncio
    async def test_process_webhook_success(self):
        """Test complete webhook processing success flow."""
        headers = {"Authorization": "Bearer test_secret"}
        body = json.dumps({
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "call_id": "webhook-test-123",
                        "sdp": "mock-sdp",
                        "event": "call.initiated"
                    }
                }]
            }]
        }).encode('utf-8')
        
        with patch('app.webhook_handler.config.WHATSAPP_WEBHOOK_SECRET', 'test_secret'), \
             patch('app.webhook_handler.call_session_manager') as mock_manager:
            
            mock_manager.handle_new_call = AsyncMock()
            
            status_code, response_data = await self.handler.process_webhook(headers, body)
            
            assert status_code == 200
            assert response_data["status"] == "success"
            
    @pytest.mark.asyncio 
    async def test_process_webhook_unauthorized(self):
        """Test webhook processing with invalid auth."""
        headers = {"Authorization": "Bearer wrong_token"}
        body = b'{"test": "data"}'
        
        with patch('app.webhook_handler.config.WHATSAPP_WEBHOOK_SECRET', 'correct_token'):
            status_code, response_data = await self.handler.process_webhook(headers, body)
            
            assert status_code == 401
            assert response_data["error"] == "Unauthorized"
            
    @pytest.mark.asyncio
    async def test_process_webhook_invalid_json(self):
        """Test webhook processing with invalid JSON."""
        headers = {"Authorization": "Bearer test_secret"}
        body = b'invalid json{'
        
        with patch('app.webhook_handler.config.WHATSAPP_WEBHOOK_SECRET', 'test_secret'):
            status_code, response_data = await self.handler.process_webhook(headers, body)
            
            assert status_code == 400
            assert response_data["error"] == "Invalid JSON payload"


if __name__ == "__main__":
    pytest.main([__file__])
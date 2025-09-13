"""
Tests for call session management functionality.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.call_session import CallSession, CallSessionManager
from app.webrtc_adapter import MockMediaSessionHandle


class TestCallSession:
    """Test cases for CallSession class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.call_id = "test-call-session-123"
        self.phone_number_id = "test-phone-456"
        self.session = CallSession(self.call_id, self.phone_number_id)
        
    @pytest.mark.asyncio
    async def test_handle_call_initiation_success(self):
        """Test successful call initiation handling."""
        offer_sdp = "v=0\no=- 123 2 IN IP4 127.0.0.1"
        
        # Mock dependencies
        with patch('app.call_session.webrtc_adapter') as mock_webrtc, \
             patch('app.call_session.whatsapp_client') as mock_whatsapp, \
             patch('app.call_session.openai_realtime_client') as mock_openai, \
             patch.object(self.session, '_start_conversation') as mock_start_conv:
            
            # Setup mocks
            mock_webrtc.create_answer.return_value = "mock-answer-sdp"
            mock_media_session = MagicMock(spec=MockMediaSessionHandle)
            mock_webrtc.connect_media = AsyncMock(return_value=mock_media_session)
            mock_whatsapp.answer_call = AsyncMock(return_value={"success": True})
            mock_openai.initialize_session = AsyncMock()
            mock_start_conv.return_value = None
            
            # Execute
            await self.session.handle_call_initiation(offer_sdp)
            
            # Verify calls
            mock_webrtc.create_answer.assert_called_once_with(offer_sdp)
            mock_whatsapp.answer_call.assert_called_once_with(
                phone_number_id=self.phone_number_id,
                call_id=self.call_id,
                sdp_answer="mock-answer-sdp"
            )
            mock_webrtc.connect_media.assert_called_once_with(
                call_id=self.call_id,
                local_sdp="mock-answer-sdp",
                remote_sdp=offer_sdp
            )
            mock_openai.initialize_session.assert_called_once()
            mock_start_conv.assert_called_once()
            
            # Verify state
            assert self.session.is_active is True
            assert self.session.media_session == mock_media_session
            
    @pytest.mark.asyncio
    async def test_handle_call_initiation_error(self):
        """Test call initiation handling with error."""
        offer_sdp = "v=0\no=- 123 2 IN IP4 127.0.0.1"
        
        with patch('app.call_session.webrtc_adapter') as mock_webrtc, \
             patch.object(self.session, '_cleanup') as mock_cleanup:
            
            # Make webrtc adapter fail
            mock_webrtc.create_answer.side_effect = Exception("WebRTC error")
            mock_cleanup.return_value = None
            
            # Execute and expect exception
            with pytest.raises(Exception) as exc_info:
                await self.session.handle_call_initiation(offer_sdp)
                
            assert "WebRTC error" in str(exc_info.value)
            mock_cleanup.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_speak_initial_greeting(self):
        """Test AI speaking initial greeting."""
        # Mock media session
        mock_media_session = MagicMock(spec=MockMediaSessionHandle)
        mock_media_session.send_audio = AsyncMock()
        self.session.media_session = mock_media_session
        self.session.is_active = True
        
        # Mock OpenAI client
        with patch('app.call_session.openai_realtime_client') as mock_openai:
            mock_openai.speak_initial_greeting = AsyncMock()
            
            # Mock async generator for audio chunks
            async def mock_audio_generator():
                yield b"audio_chunk_1"
                yield b"audio_chunk_2"
                
            mock_openai.handle_response_events.return_value = mock_audio_generator()
            
            # Execute
            await self.session._speak_initial_greeting()
            
            # Verify calls
            mock_openai.speak_initial_greeting.assert_called_once()
            assert mock_media_session.send_audio.call_count == 2
            mock_media_session.send_audio.assert_any_call(b"audio_chunk_1")
            mock_media_session.send_audio.assert_any_call(b"audio_chunk_2")
            
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test session cleanup."""
        # Setup mock media session and tasks
        mock_media_session = MagicMock(spec=MockMediaSessionHandle)
        mock_media_session.close = AsyncMock()
        self.session.media_session = mock_media_session
        
        mock_task = MagicMock()
        mock_task.done.return_value = False
        self.session.audio_tasks = [mock_task]
        
        with patch('app.call_session.openai_realtime_client') as mock_openai:
            mock_openai.disconnect = AsyncMock()
            
            # Execute
            await self.session._cleanup()
            
            # Verify cleanup
            assert self.session.is_active is False
            mock_task.cancel.assert_called_once()
            mock_media_session.close.assert_called_once()
            mock_openai.disconnect.assert_called_once()
            assert self.session.media_session is None


class TestCallSessionManager:
    """Test cases for CallSessionManager class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = CallSessionManager()
        
    @pytest.mark.asyncio
    async def test_handle_new_call(self):
        """Test handling new call creation."""
        call_id = "manager-test-call-789"
        offer_sdp = "mock-offer-sdp"
        phone_number_id = "manager-phone-123"
        
        # Mock CallSession
        with patch('app.call_session.CallSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.call_id = call_id
            mock_session.handle_call_initiation = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Execute
            await self.manager.handle_new_call(call_id, offer_sdp, phone_number_id)
            
            # Allow async task to start
            await asyncio.sleep(0.01)
            
            # Verify session creation
            mock_session_class.assert_called_once_with(call_id, phone_number_id)
            assert call_id in self.manager.active_sessions
            assert self.manager.active_sessions[call_id] == mock_session
            
    @pytest.mark.asyncio
    async def test_handle_duplicate_call(self):
        """Test handling duplicate call ID."""
        call_id = "duplicate-call-123"
        
        # Add existing session
        existing_session = MagicMock()
        existing_session.end_call = AsyncMock()
        self.manager.active_sessions[call_id] = existing_session
        
        with patch('app.call_session.CallSession') as mock_session_class:
            mock_new_session = MagicMock()
            mock_new_session.call_id = call_id
            mock_new_session.handle_call_initiation = AsyncMock()
            mock_session_class.return_value = mock_new_session
            
            # Execute
            await self.manager.handle_new_call(call_id, "mock-sdp", "phone123")
            
            # Verify old session was ended
            existing_session.end_call.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_end_call(self):
        """Test ending a specific call."""
        call_id = "end-call-test-456"
        
        # Add session to manager
        mock_session = MagicMock()
        mock_session.end_call = AsyncMock()
        self.manager.active_sessions[call_id] = mock_session
        
        # Execute
        await self.manager.end_call(call_id)
        
        # Verify
        mock_session.end_call.assert_called_once()
        assert call_id not in self.manager.active_sessions
        
    @pytest.mark.asyncio
    async def test_end_all_calls(self):
        """Test ending all active calls."""
        # Add multiple sessions
        sessions = {}
        for i in range(3):
            call_id = f"call-{i}"
            mock_session = MagicMock()
            mock_session.end_call = AsyncMock()
            sessions[call_id] = mock_session
            self.manager.active_sessions[call_id] = mock_session
            
        # Execute
        await self.manager.end_all_calls()
        
        # Verify all sessions ended
        for session in sessions.values():
            session.end_call.assert_called_once()
            
        assert len(self.manager.active_sessions) == 0
        
    def test_get_active_call_count(self):
        """Test getting active call count."""
        assert self.manager.get_active_call_count() == 0
        
        # Add some mock sessions
        for i in range(5):
            self.manager.active_sessions[f"call-{i}"] = MagicMock()
            
        assert self.manager.get_active_call_count() == 5


if __name__ == "__main__":
    pytest.main([__file__])
"""
Tests for mock WebRTC adapter functionality.
"""
import asyncio
import pytest
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.webrtc_adapter import MockWebRTCAdapter, MockMediaSessionHandle


class TestMockWebRTCAdapter:
    """Test cases for MockWebRTCAdapter class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = MockWebRTCAdapter()
        
    def test_create_answer(self):
        """Test SDP answer creation."""
        offer_sdp = """v=0
o=- 123456789 2 IN IP4 192.168.1.100
s=-
t=0 0
m=audio 5004 UDP/TLS/RTP/SAVPF 111
c=IN IP4 192.168.1.100
a=rtpmap:111 opus/48000/2"""
        
        answer_sdp = self.adapter.create_answer(offer_sdp)
        
        # Verify answer structure
        assert answer_sdp.startswith("v=0")
        assert "m=audio" in answer_sdp
        assert "a=rtpmap:111 opus/48000/2" in answer_sdp
        assert "a=setup:active" in answer_sdp
        
    @pytest.mark.asyncio
    async def test_connect_media(self):
        """Test media session connection."""
        call_id = "test-media-call-123"
        local_sdp = "mock-local-sdp"
        remote_sdp = "mock-remote-sdp"
        
        # Execute
        session = await self.adapter.connect_media(call_id, local_sdp, remote_sdp)
        
        # Verify session creation
        assert isinstance(session, MockMediaSessionHandle)
        assert session.call_id == call_id
        assert call_id in self.adapter.sessions
        assert self.adapter.sessions[call_id] == session
        
    @pytest.mark.asyncio
    async def test_disconnect_media(self):
        """Test media session disconnection."""
        call_id = "test-disconnect-call-456"
        
        # Create a session first
        session = await self.adapter.connect_media(call_id, "local", "remote")
        
        # Disconnect
        await self.adapter.disconnect_media(call_id)
        
        # Verify cleanup
        assert call_id not in self.adapter.sessions


class TestMockMediaSessionHandle:
    """Test cases for MockMediaSessionHandle class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.call_id = "mock-session-test-789"
        self.session = MockMediaSessionHandle(self.call_id)
        
    @pytest.mark.asyncio
    async def test_send_audio(self):
        """Test sending audio data."""
        audio_data = b"mock_audio_data_12345"
        
        # Execute - should not raise exception
        await self.session.send_audio(audio_data)
        
        # Test with closed session
        await self.session.close()
        
        with pytest.raises(RuntimeError, match="Media session is closed"):
            await self.session.send_audio(audio_data)
            
    @pytest.mark.asyncio
    async def test_receive_audio(self):
        """Test receiving audio data stream."""
        # Collect audio chunks with timeout
        audio_chunks = []
        
        async def collect_audio():
            async for chunk in self.session.receive_audio():
                audio_chunks.append(chunk)
                if len(audio_chunks) >= 3:  # Collect a few chunks
                    break
                    
        # Run with timeout to avoid infinite loop
        try:
            await asyncio.wait_for(collect_audio(), timeout=0.2)
        except asyncio.TimeoutError:
            pass  # Expected for this test
            
        # Verify we received some chunks
        assert len(audio_chunks) > 0
        
        # Verify chunk properties
        for chunk in audio_chunks:
            assert isinstance(chunk, bytes)
            assert len(chunk) == 1024  # Mock chunk size
            
    @pytest.mark.asyncio
    async def test_receive_audio_when_closed(self):
        """Test receive audio with closed session."""
        await self.session.close()
        
        # Should return immediately when closed
        chunks = []
        async for chunk in self.session.receive_audio():
            chunks.append(chunk)
            
        assert len(chunks) == 0
        
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the media session."""
        assert not self.session.is_closed
        
        await self.session.close()
        
        assert self.session.is_closed
        
        # Calling close again should be safe
        await self.session.close()
        
    @pytest.mark.asyncio
    async def test_receive_audio_cancellation(self):
        """Test cancelling audio reception."""
        # Start receiving audio
        receive_task = asyncio.create_task(
            self._collect_audio_chunks(self.session)
        )
        
        # Let it run briefly
        await asyncio.sleep(0.05)
        
        # Cancel the task
        receive_task.cancel()
        
        # Should handle cancellation gracefully
        try:
            await receive_task
        except asyncio.CancelledError:
            pass  # Expected
            
    async def _collect_audio_chunks(self, session):
        """Helper to collect audio chunks."""
        chunks = []
        async for chunk in session.receive_audio():
            chunks.append(chunk)
        return chunks


class TestWebRTCAdapterInterface:
    """Test cases for WebRTC adapter interface compliance."""
    
    @pytest.mark.asyncio
    async def test_adapter_interface_methods(self):
        """Test that adapter implements required interface methods."""
        adapter = MockWebRTCAdapter()
        
        # Test create_answer
        answer = adapter.create_answer("mock-offer")
        assert isinstance(answer, str)
        assert len(answer) > 0
        
        # Test connect_media
        session = await adapter.connect_media("test-call", "local", "remote")
        assert hasattr(session, 'send_audio')
        assert hasattr(session, 'receive_audio')
        assert hasattr(session, 'close')
        
        # Test session methods
        await session.send_audio(b"test")
        
        # Test receive_audio returns async generator
        receive_gen = session.receive_audio()
        assert hasattr(receive_gen, '__aiter__')
        
        await session.close()
        
    def test_mock_implementation_markers(self):
        """Test that mock implementation has appropriate TODO markers."""
        import inspect
        
        # Check create_answer method has TODO
        source = inspect.getsource(MockWebRTCAdapter.create_answer)
        assert "TODO" in source
        
        # Check connect_media method has TODO
        source = inspect.getsource(MockWebRTCAdapter.connect_media)
        assert "TODO" in source


if __name__ == "__main__":
    pytest.main([__file__])
"""
OpenAI Realtime API wrapper for voice conversations.
Handles connection, audio streaming, and conversation management using standard library.
"""
import asyncio
import json
import logging
import ssl
import base64
from typing import Optional, AsyncGenerator, Dict, Any
from urllib.parse import urlparse

from .config import config
from .medicine_context import get_system_prompt, get_medicine_context, get_initial_greeting
from .utils import log_openai_event


class OpenAIRealtimeClient:
    """Client for OpenAI Realtime API using standard library WebSocket implementation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False
        
    async def connect(self) -> None:
        """Establish connection to OpenAI Realtime API."""
        if self.is_connected:
            return
            
        # For now, implement a mock connection since WebSocket requires additional dependencies
        # TODO: In production, use a proper WebSocket client library or implement WebSocket handshake
        log_openai_event("connect", "Mock connection to OpenAI Realtime API (TODO: implement real WebSocket)")
        self.is_connected = True
            
    async def disconnect(self) -> None:
        """Close connection."""
        if self.is_connected:
            self.is_connected = False
            log_openai_event("disconnect", "Disconnected from OpenAI Realtime API")
                
    async def send_event(self, event: Dict[str, Any]) -> None:
        """Send event to OpenAI Realtime API."""
        if not self.is_connected:
            raise RuntimeError("Not connected to OpenAI Realtime API")
            
        # Mock sending event
        log_openai_event("send_event", f"Mock sent event: {event.get('type', 'unknown')}")
            
    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Receive events from OpenAI Realtime API."""
        if not self.is_connected:
            raise RuntimeError("Not connected to OpenAI Realtime API")
            
        # Mock receiving events
        log_openai_event("receive_events", "Mock receiving events")
        
        # Simulate session created event
        yield {"type": "session.created", "session": {"id": "mock_session"}}
        
        # Simulate session updated event  
        yield {"type": "session.updated"}
        
        # Keep connection alive with periodic mock events
        while self.is_connected:
            await asyncio.sleep(1.0)
            # Mock audio response
            mock_audio = base64.b64encode(b'\x00' * 160).decode('utf-8')  # 160 bytes = 10ms at 16kHz
            yield {
                "type": "response.audio.delta",
                "delta": mock_audio
            }
            
    async def initialize_session(self) -> None:
        """Initialize the OpenAI Realtime session with medicine context."""
        if not self.is_connected:
            await self.connect()
            
        # Configure session with medicine context
        medicine_context = get_medicine_context()
        system_prompt = get_system_prompt()
        
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": f"{system_prompt}\n\nMedicine context: {json.dumps(medicine_context)}",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                }
            }
        }
        
        await self.send_event(session_config)
        log_openai_event("initialize_session", "Session initialized with medicine context")
        
    async def speak_initial_greeting(self) -> None:
        """Have the AI speak the initial medicine reminder greeting."""
        greeting = get_initial_greeting()
        
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["audio"],
                "instructions": f"Say exactly: '{greeting}'"
            }
        }
        
        await self.send_event(response_create)
        log_openai_event("speak_initial_greeting", f"Requested AI to say: '{greeting}'")
        
    async def send_user_audio(self, audio_data: bytes) -> None:
        """Send user audio data to OpenAI for processing."""
        audio_event = {
            "type": "input_audio.append",
            "audio": base64.b64encode(audio_data).decode('utf-8')
        }
        
        await self.send_event(audio_event)
        log_openai_event("send_user_audio", f"Sent {len(audio_data)} bytes of user audio")
        
    async def commit_user_audio(self) -> None:
        """Commit buffered user audio for processing."""
        commit_event = {
            "type": "input_audio.commit"
        }
        
        await self.send_event(commit_event)
        log_openai_event("commit_user_audio", "Committed user audio for processing")
        
    async def handle_response_events(self) -> AsyncGenerator[bytes, None]:
        """Handle response events and yield audio data."""
        async for event in self.receive_events():
            event_type = event.get("type")
            
            if event_type == "response.audio.delta":
                # Decode base64 audio data
                audio_data = base64.b64decode(event.get("delta", ""))
                log_openai_event("response_audio", f"Received {len(audio_data)} bytes of AI audio")
                yield audio_data
                
            elif event_type == "response.audio.done":
                log_openai_event("response_audio", "AI audio response complete")
                
            elif event_type == "error":
                error_msg = event.get("error", {}).get("message", "Unknown error")
                log_openai_event("error", f"OpenAI error: {error_msg}")
                raise RuntimeError(f"OpenAI error: {error_msg}")
                
            elif event_type == "session.created":
                log_openai_event("session_created", "OpenAI session created")
                
            elif event_type == "session.updated":
                log_openai_event("session_updated", "OpenAI session updated")


# Global client instance
openai_realtime_client = OpenAIRealtimeClient()
"""
Call session management for orchestrating WhatsApp voice calls with OpenAI Realtime.
Handles the complete call lifecycle from webhook to AI conversation.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from .config import config
from .whatsapp_client import whatsapp_client
from .openai_realtime import openai_realtime_client
from .webrtc_adapter import webrtc_adapter, MediaSessionHandle
from .medicine_context import get_initial_greeting
from .utils import log_call_session, log_openai_event, log_webrtc_event


class CallSession:
    """Manages a single WhatsApp voice call session with OpenAI integration."""
    
    def __init__(self, call_id: str, phone_number_id: str = "mock_phone_id"):
        self.call_id = call_id
        self.phone_number_id = phone_number_id
        self.logger = logging.getLogger(__name__)
        self.media_session: Optional[MediaSessionHandle] = None
        self.is_active = False
        self.audio_tasks = []
        
    async def handle_call_initiation(self, offer_sdp: str) -> None:
        """
        Handle incoming call initiation with SDP offer.
        
        Args:
            offer_sdp: SDP offer from WhatsApp
        """
        try:
            log_call_session(self.call_id, "initiation", "Processing call initiation")
            
            # Step 1: Generate SDP answer
            log_call_session(self.call_id, "sdp_answer", "Creating SDP answer")
            answer_sdp = webrtc_adapter.create_answer(offer_sdp)
            
            # Step 2: Send answer to WhatsApp API
            log_call_session(self.call_id, "answer_call", "Sending call answer to WhatsApp")
            await whatsapp_client.answer_call(
                phone_number_id=self.phone_number_id,
                call_id=self.call_id,
                sdp_answer=answer_sdp
            )
            
            # Step 3: Establish media session
            log_call_session(self.call_id, "media_session", "Establishing media session")
            self.media_session = await webrtc_adapter.connect_media(
                call_id=self.call_id,
                local_sdp=answer_sdp,
                remote_sdp=offer_sdp
            )
            
            # Step 4: Initialize OpenAI Realtime
            log_call_session(self.call_id, "openai_init", "Initializing OpenAI Realtime session")
            await openai_realtime_client.initialize_session()
            
            # Step 5: Start the conversation
            self.is_active = True
            await self._start_conversation()
            
        except Exception as e:
            self.logger.error(f"Error handling call initiation for {self.call_id}: {e}")
            await self._cleanup()
            raise
            
    async def _start_conversation(self) -> None:
        """Start the AI conversation flow."""
        if not self.media_session:
            raise RuntimeError("Media session not established")
            
        log_call_session(self.call_id, "conversation_start", "Starting AI conversation")
        
        try:
            # Step 1: AI speaks first - medicine reminder
            await self._speak_initial_greeting()
            
            # Step 2: Set up bidirectional audio streaming
            audio_receive_task = asyncio.create_task(
                self._handle_incoming_audio()
            )
            audio_send_task = asyncio.create_task(
                self._handle_outgoing_audio()
            )
            
            self.audio_tasks = [audio_receive_task, audio_send_task]
            
            # Step 3: Wait for call completion or timeout
            timeout_task = asyncio.create_task(
                asyncio.sleep(config.CALL_TIMEOUT_SECONDS)
            )
            
            done, pending = await asyncio.wait(
                self.audio_tasks + [timeout_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
            log_call_session(self.call_id, "conversation_end", "AI conversation ended")
            
        except Exception as e:
            self.logger.error(f"Error in conversation for {self.call_id}: {e}")
        finally:
            await self._cleanup()
            
    async def _speak_initial_greeting(self) -> None:
        """Have AI speak the initial medicine reminder."""
        log_call_session(self.call_id, "initial_greeting", "AI speaking initial greeting")
        
        # Request AI to speak the greeting
        await openai_realtime_client.speak_initial_greeting()
        
        # Handle the AI audio response and send to call
        async for audio_chunk in openai_realtime_client.handle_response_events():
            if self.media_session and self.is_active:
                await self.media_session.send_audio(audio_chunk)
            else:
                break
                
        log_call_session(self.call_id, "initial_greeting", "Initial greeting completed")
        
    async def _handle_incoming_audio(self) -> None:
        """Handle incoming audio from the call and send to OpenAI."""
        if not self.media_session:
            return
            
        log_call_session(self.call_id, "incoming_audio", "Started handling incoming audio")
        
        try:
            async for audio_chunk in self.media_session.receive_audio():
                if not self.is_active:
                    break
                    
                # Send user audio to OpenAI
                await openai_realtime_client.send_user_audio(audio_chunk)
                
                # Periodically commit audio for processing
                await asyncio.sleep(0.1)  # Small delay to batch audio
                await openai_realtime_client.commit_user_audio()
                
        except Exception as e:
            log_call_session(self.call_id, "incoming_audio", f"Error: {e}")
        finally:
            log_call_session(self.call_id, "incoming_audio", "Stopped handling incoming audio")
            
    async def _handle_outgoing_audio(self) -> None:
        """Handle outgoing audio from OpenAI and send to the call."""
        if not self.media_session:
            return
            
        log_call_session(self.call_id, "outgoing_audio", "Started handling outgoing audio")
        
        try:
            async for audio_chunk in openai_realtime_client.handle_response_events():
                if not self.is_active:
                    break
                    
                # Send AI audio to the call
                await self.media_session.send_audio(audio_chunk)
                
        except Exception as e:
            log_call_session(self.call_id, "outgoing_audio", f"Error: {e}")
        finally:
            log_call_session(self.call_id, "outgoing_audio", "Stopped handling outgoing audio")
            
    async def end_call(self) -> None:
        """End the call session gracefully."""
        log_call_session(self.call_id, "end_call", "Ending call session")
        self.is_active = False
        await self._cleanup()
        
    async def _cleanup(self) -> None:
        """Clean up resources for the call session."""
        log_call_session(self.call_id, "cleanup", "Cleaning up call session")
        
        self.is_active = False
        
        # Cancel audio tasks
        for task in self.audio_tasks:
            if not task.done():
                task.cancel()
                
        # Close media session
        if self.media_session:
            try:
                await self.media_session.close()
            except Exception as e:
                self.logger.error(f"Error closing media session: {e}")
            finally:
                self.media_session = None
                
        # Disconnect from OpenAI
        try:
            await openai_realtime_client.disconnect()
        except Exception as e:
            self.logger.error(f"Error disconnecting from OpenAI: {e}")
            
        log_call_session(self.call_id, "cleanup", "Call session cleanup completed")


class CallSessionManager:
    """Manages multiple active call sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, CallSession] = {}
        self.logger = logging.getLogger(__name__)
        
    async def handle_new_call(self, call_id: str, offer_sdp: str, phone_number_id: str = "mock_phone_id") -> None:
        """Handle a new incoming call."""
        if call_id in self.active_sessions:
            self.logger.warning(f"Call {call_id} already exists, ending previous session")
            await self.end_call(call_id)
            
        self.logger.info(f"Creating new call session for {call_id}")
        session = CallSession(call_id, phone_number_id)
        self.active_sessions[call_id] = session
        
        # Handle call initiation in background
        asyncio.create_task(self._handle_call_async(session, offer_sdp))
        
    async def _handle_call_async(self, session: CallSession, offer_sdp: str) -> None:
        """Handle call session asynchronously."""
        try:
            await session.handle_call_initiation(offer_sdp)
        except Exception as e:
            self.logger.error(f"Error in call session {session.call_id}: {e}")
        finally:
            # Remove from active sessions
            if session.call_id in self.active_sessions:
                del self.active_sessions[session.call_id]
                
    async def end_call(self, call_id: str) -> None:
        """End a specific call session."""
        if call_id in self.active_sessions:
            await self.active_sessions[call_id].end_call()
            del self.active_sessions[call_id]
            
    async def end_all_calls(self) -> None:
        """End all active call sessions."""
        sessions = list(self.active_sessions.values())
        self.active_sessions.clear()
        
        await asyncio.gather(
            *[session.end_call() for session in sessions],
            return_exceptions=True
        )
        
    def get_active_call_count(self) -> int:
        """Get the number of active call sessions."""
        return len(self.active_sessions)


# Global call session manager
call_session_manager = CallSessionManager()
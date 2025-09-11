"""
CaptureSession class for managing individual audio capture sessions.
Replaces global _capture state with proper session management.
"""

import asyncio
import uuid
import time
from typing import Optional, Dict, Any, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SessionState(Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class CaptureSession:
    """Manages an individual dual-channel audio capture session."""
    
    def __init__(self, session_id: str, config: Dict[str, Any]):
        self.session_id = session_id
        self.config = config
        self.state = SessionState.CREATED
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.stopped_at: Optional[float] = None
        self.error_message: Optional[str] = None
        
        # Concurrency control
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        
        # Audio capture state
        self._capture_instance = None
        self._audio_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.data_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # Metrics
        self.total_frames_captured = 0
        self.total_chunks_processed = 0
        self.last_chunk_timestamp: Optional[float] = None
        
        logger.info(f"Created capture session {session_id}")
    
    async def initialize(self) -> bool:
        """Initialize the capture session."""
        async with self._lock:
            if self.state != SessionState.CREATED:
                logger.warning(f"Session {self.session_id} already initialized")
                return self.state in [SessionState.READY, SessionState.ACTIVE]
            
            self.state = SessionState.INITIALIZING
            
            try:
                # Initialize audio capture (implementation specific)
                # This would interface with the actual audio capture implementation
                logger.info(f"Initializing capture for session {self.session_id}")
                
                # Simulate initialization
                await asyncio.sleep(0.1)  # Replace with actual initialization
                
                self.state = SessionState.READY
                logger.info(f"Session {self.session_id} initialized successfully")
                return True
                
            except Exception as e:
                self.error_message = str(e)
                self.state = SessionState.ERROR
                logger.error(f"Failed to initialize session {self.session_id}: {e}")
                return False
    
    async def start(self) -> bool:
        """Start audio capture."""
        async with self._lock:
            if self.state == SessionState.ACTIVE:
                logger.warning(f"Session {self.session_id} already active")
                return True
            
            if self.state != SessionState.READY:
                logger.error(f"Session {self.session_id} not ready (state: {self.state})")
                return False
            
            self.state = SessionState.STARTING
            
            try:
                # Start actual audio capture
                logger.info(f"Starting capture for session {self.session_id}")
                
                # Clear stop event
                self._stop_event.clear()
                
                # Start audio processing task
                self._audio_task = asyncio.create_task(self._audio_processing_loop())
                
                self.started_at = time.time()
                self.state = SessionState.ACTIVE
                logger.info(f"Session {self.session_id} started successfully")
                return True
                
            except Exception as e:
                self.error_message = str(e)
                self.state = SessionState.ERROR
                logger.error(f"Failed to start session {self.session_id}: {e}")
                return False
    
    async def stop(self) -> bool:
        """Stop audio capture."""
        async with self._lock:
            if self.state in [SessionState.STOPPED, SessionState.STOPPING]:
                logger.warning(f"Session {self.session_id} already stopped/stopping")
                return True
            
            if self.state != SessionState.ACTIVE:
                logger.warning(f"Session {self.session_id} not active (state: {self.state})")
                return True
            
            self.state = SessionState.STOPPING
            
            try:
                logger.info(f"Stopping capture for session {self.session_id}")
                
                # Signal stop
                self._stop_event.set()
                
                # Wait for audio task to complete
                if self._audio_task:
                    try:
                        await asyncio.wait_for(self._audio_task, timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"Audio task timeout for session {self.session_id}")
                        self._audio_task.cancel()
                    except Exception as e:
                        logger.warning(f"Audio task error for session {self.session_id}: {e}")
                
                self.stopped_at = time.time()
                self.state = SessionState.STOPPED
                logger.info(f"Session {self.session_id} stopped successfully")
                return True
                
            except Exception as e:
                self.error_message = str(e)
                self.state = SessionState.ERROR
                logger.error(f"Failed to stop session {self.session_id}: {e}")
                return False
    
    async def cleanup(self):
        """Clean up session resources."""
        if self.state == SessionState.ACTIVE:
            await self.stop()
        
        # Clean up resources
        if self._audio_task and not self._audio_task.done():
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Session {self.session_id} cleaned up")
    
    async def _audio_processing_loop(self):
        """Main audio processing loop."""
        try:
            while not self._stop_event.is_set():
                # Simulate audio processing
                await asyncio.sleep(0.01)  # 10ms chunks
                
                # Update metrics
                self.total_chunks_processed += 1
                self.last_chunk_timestamp = time.time()
                
                # Call data callback if set
                if self.data_callback:
                    try:
                        await self.data_callback(self.session_id, b"dummy_audio_data")
                    except Exception as e:
                        logger.error(f"Data callback error for session {self.session_id}: {e}")
                
        except Exception as e:
            logger.error(f"Audio processing error for session {self.session_id}: {e}")
            if self.error_callback:
                await self.error_callback(self.session_id, str(e))
    
    def get_info(self) -> Dict[str, Any]:
        """Get session information."""
        duration = None
        if self.started_at:
            end_time = self.stopped_at or time.time()
            duration = end_time - self.started_at
        
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "duration": duration,
            "error_message": self.error_message,
            "config": self.config,
            "metrics": {
                "total_frames_captured": self.total_frames_captured,
                "total_chunks_processed": self.total_chunks_processed,
                "last_chunk_timestamp": self.last_chunk_timestamp
            }
        }
    
    @property
    def is_active(self) -> bool:
        """Check if session is actively capturing."""
        return self.state == SessionState.ACTIVE
    
    @property
    def is_ready(self) -> bool:
        """Check if session is ready to start."""
        return self.state == SessionState.READY
    
    @property
    def has_error(self) -> bool:
        """Check if session has an error."""
        return self.state == SessionState.ERROR
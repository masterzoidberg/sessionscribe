from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
import base64
import logging
import time
import uuid
import os
from datetime import datetime
from typing import Dict, Optional, Any
import asyncio
import threading
# Lazy import - whisper_stream will be imported when needed

# Import centralized configuration and logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.config import settings
from shared.logging_config import setup_structured_logging

# Configure structured logging
logger = setup_structured_logging("asr", settings.asr_port)

app = FastAPI(title="SessionScribe ASR Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3001", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

# Minimal global state - only track active capture session
_capture = None
_capture_session_id: Optional[str] = None

# Models
class StreamStartRequest(BaseModel):
    sample_rate: int = 48000
    channels: int = 2
    format: str = "pcm_s16le"

class StreamChunkRequest(BaseModel):
    session_id: str
    pcm_chunk_base64: str

class StreamStopRequest(BaseModel):
    session_id: str

# Phase 4 Stereo Models
class StereoStartRequest(BaseModel):
    sample_rate: int = 48000
    chunk_ms: int = 1000
    vad_enabled: bool = True
    auto_balance: str = "off"  # "off" or "auto"
    mic_device: Optional[int] = None
    loopback_device: Optional[int] = None

class StereoStopRequest(BaseModel):
    session_id: str

class StereoChunkRequest(BaseModel):
    session_id: str
    channel: str  # "L" or "R"
    pcm_chunk_base64: str
    client_timestamp: Optional[int] = None

# Dual-Channel Tagged Models
class DualChannelStartRequest(BaseModel):
    sample_rate: int = 44100
    mic_device_id: Optional[conint(ge=0)] = None
    output_device_id: Optional[conint(ge=0)] = None
    buffer_size_ms: int = 100
    exclusive_mode: bool = False

class DualChannelStopRequest(BaseModel):
    session_id: str

class DualChannelChunkRequest(BaseModel):
    session_id: str
    channel: str  # "therapist" or "client"
    pcm_chunk_base64: str
    timestamp: Optional[float] = None

# Removed background processing to simplify startup - transcription will be handled via direct endpoint calls

# Legacy streaming endpoints removed to simplify startup - focus on dual-channel WASAPI


# Stereo endpoints removed to simplify startup - focus on dual-channel WASAPI

@app.get("/devices")
async def get_devices():
    """Get available audio devices with loopback detection"""
    try:
        # Lazy import audio modules
        from audio_wasapi import list_devices
        devices = list_devices()
        return devices
    except Exception as e:
        logger.error(f"Error listing devices", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Device enumeration failed: {str(e)}")

@app.get("/health")
async def health():
    """Immediate health check endpoint"""
    return {
        "status": "ok",
        "service": "asr",
        "capture_active": _capture is not None,
        "active_session_id": _capture_session_id
    }

# Dual-Channel Tagged Stream Endpoints
@app.post("/dual-channel/start")
async def dual_channel_start(request: DualChannelStartRequest):
    """Start dual-channel tagged audio capture session"""
    global _capture, _capture_session_id
    
    # Check if already running
    if _capture is not None:
        logger.warning("Dual-channel capture already running")
        raise HTTPException(status_code=409, detail="Capture already running")
    
    try:
        # Lazy import audio modules
        logger.info("Importing audio modules...")
        from audio_wasapi import DualCapture, WasapiSettings
        import numpy as np
        
        session_id = str(uuid.uuid4())
        logger.info("dual_channel_session_start", session_id=session_id)
        
        # Configure WASAPI settings
        settings = WasapiSettings(
            sample_rate=request.sample_rate,
            channels=1,
            dtype=np.float32,
            exclusive=request.exclusive_mode,
            latency='low'
        )
        
        # Create dual capture instance
        dual_capture = DualCapture(
            settings=settings,
            buffer_size_ms=request.buffer_size_ms,
            mic_device_id=request.mic_device_id,
            output_device_id=request.output_device_id
        )
        
        # Start capture
        logger.info(f"Starting audio capture with mic_device_id={request.mic_device_id}, output_device_id={request.output_device_id}")
        # Note: DualCapture.start() will be called when audio callback is set up
        
        _capture = dual_capture
        _capture_session_id = session_id
        
        logger.info(f"Dual-channel session started successfully: {session_id}")
        return {
            "session_id": session_id,
            "success": True,
            "sample_rate": request.sample_rate,
            "buffer_size_ms": request.buffer_size_ms
        }
        
    except Exception as e:
        logger.error(f"Failed to start dual-channel session", exc_info=True)
        _capture = None
        _capture_session_id = None
        raise HTTPException(status_code=500, detail=f"Audio initialization failed: {str(e)}")

@app.post("/dual-channel/chunk")
async def dual_channel_chunk(request: DualChannelChunkRequest):
    """Process tagged audio chunk from dual-channel capture (stateless)"""
    try:
        # Validate session exists and is active
        if _capture_session_id != request.session_id:
            raise HTTPException(status_code=404, detail="Invalid or inactive session")
        
        # Validate channel tag
        if request.channel not in ["therapist", "client"]:
            raise HTTPException(status_code=400, detail="Invalid channel tag. Use 'therapist' or 'client'")
        
        # Process audio chunk immediately (no queuing to prevent memory leaks)
        try:
            # TODO: Replace with real transcription processing
            # For now, just acknowledge the chunk without storing it
            logger.info("audio_chunk_received", 
                       session_id=request.session_id, 
                       channel=request.channel,
                       timestamp=request.timestamp or time.time())
            
            # In a real implementation, this would:
            # 1. Decode base64 audio
            # 2. Send to transcription engine
            # 3. Return transcription result or acknowledgment
            
        except Exception as processing_error:
            logger.error("audio_chunk_processing_failed", 
                        session_id=request.session_id,
                        channel=request.channel, 
                        error=str(processing_error))
            raise HTTPException(status_code=500, detail="Audio processing failed")
        
        # Return immediate acknowledgment
        return {
            "success": True,
            "session_id": request.session_id,
            "channel": request.channel,
            "processed_at": time.time()
        }
        
    except Exception as e:
        logger.error("dual_channel_chunk_error", 
                    session_id=request.session_id if hasattr(request, 'session_id') else 'unknown',
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dual-channel/stop")
async def dual_channel_stop(request: DualChannelStopRequest):
    """Stop dual-channel capture session"""
    global _capture, _capture_session_id
    
    # Check if capture is running and matches session
    if _capture is None:
        logger.warning("No dual-channel capture running")
        raise HTTPException(status_code=404, detail="No capture session running")
    
    if _capture_session_id != request.session_id:
        logger.warning(f"Session ID mismatch: expected {_capture_session_id}, got {request.session_id}")
        raise HTTPException(status_code=404, detail="Session ID mismatch")
    
    try:
        logger.info(f"Stopping dual-channel session: {request.session_id}")
        
        # Stop capture
        if hasattr(_capture, 'stop'):
            _capture.stop()
        
        # Clean up global state
        _capture = None
        _capture_session_id = None
        
        logger.info(f"Dual-channel session stopped successfully: {request.session_id}")
        return {
            "success": True,
            "session_id": request.session_id
        }
        
    except Exception as e:
        logger.error(f"Failed to stop dual-channel session", exc_info=True)
        # Force cleanup on error
        _capture = None
        _capture_session_id = None
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")

@app.get("/dual-channel/{session_id}/status")
async def dual_channel_status(session_id: str):
    """Get dual-channel session status (stateless)"""
    try:
        # Check if this session ID matches the active capture session
        if _capture_session_id != session_id:
            raise HTTPException(status_code=404, detail="Session not found or inactive")
        
        # Return minimal status info since we're now stateless
        return {
            "session_id": session_id,
            "is_active": _capture is not None,
            "capture_running": _capture is not None,
            "message": "Session is active. Transcripts are processed in real-time without storage."
        }
        
    except Exception as e:
        logger.error(f"Error getting dual-channel status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7031, reload=True)
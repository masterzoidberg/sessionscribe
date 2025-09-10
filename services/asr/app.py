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

# Configure logging with file output
os.makedirs("scripts/logs/asr", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scripts/logs/asr/out.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Error logging handler
error_handler = logging.FileHandler("scripts/logs/asr/err.log")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(error_handler)

app = FastAPI(title="SessionScribe ASR Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3001", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

# Global state - streaming sessions
streaming_sessions: Dict[str, Dict[str, Any]] = {}
stereo_sessions: Dict[str, Dict[str, Any]] = {}
dual_channel_sessions: Dict[str, Dict[str, Any]] = {}

# Global audio capture state
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
        logger.info(f"Starting dual-channel session: {session_id}")
        
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
    """Process tagged audio chunk from dual-channel capture"""
    try:
        if request.session_id not in dual_channel_sessions:
            raise HTTPException(status_code=404, detail="Dual-channel session not found")
        
        session = dual_channel_sessions[request.session_id]
        
        # Validate channel tag
        if request.channel not in ["therapist", "client"]:
            raise HTTPException(status_code=400, detail="Invalid channel tag. Use 'therapist' or 'client'")
        
        # Add chunk to processing queue
        chunk_data = {
            'audio_base64': request.pcm_chunk_base64,
            'channel': request.channel,
            'timestamp': request.timestamp or time.time(),
            'session_id': request.session_id
        }
        
        session['pending_chunks'].append(chunk_data)
        session['total_chunks_received'] += 1
        
        # Return immediate acknowledgment (transcription happens in background)
        return {
            "success": True,
            "session_id": request.session_id,
            "channel": request.channel,
            "chunks_in_queue": len(session['pending_chunks'])
        }
        
    except Exception as e:
        logger.error(f"Error processing dual-channel chunk: {e}")
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
    """Get dual-channel session status and recent transcriptions"""
    try:
        if session_id not in dual_channel_sessions:
            raise HTTPException(status_code=404, detail="Dual-channel session not found")
        
        session = dual_channel_sessions[session_id]
        
        # Get recent transcriptions (last 3 from each channel)
        recent_transcripts = {}
        for channel in ['therapist', 'client']:
            if channel in session['transcript_chunks']:
                recent_transcripts[channel] = session['transcript_chunks'][channel][-3:] if len(session['transcript_chunks'][channel]) > 3 else session['transcript_chunks'][channel]
            else:
                recent_transcripts[channel] = []
        
        return {
            "session_id": session_id,
            "is_active": True,
            "sample_rate": session['sample_rate'],
            "buffer_size_ms": session['buffer_size_ms'],
            "session_duration": time.time() - session['start_time'],
            "recent_transcripts": recent_transcripts,
            "total_chunks": {
                "therapist": len(session['transcript_chunks'].get('therapist', [])),
                "client": len(session['transcript_chunks'].get('client', []))
            },
            "pending_chunks": len(session['pending_chunks']),
            "total_chunks_received": session['total_chunks_received']
        }
        
    except Exception as e:
        logger.error(f"Error getting dual-channel status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7031, reload=True)
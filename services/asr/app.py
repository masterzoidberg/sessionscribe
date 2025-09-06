from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from .whisper_stream import WhisperStreamer, streamer
from .audio_wasapi import WASAPIRecorder, recorder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SessionScribe ASR Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_connections: List[WebSocket] = []
is_recording = False
is_transcribing = False

# Models
class StartRecordingRequest(BaseModel):
    mic_device_id: Optional[int] = None
    loopback_device_id: Optional[int] = None
    output_path: Optional[str] = None

class TranscribeChunkRequest(BaseModel):
    audio_data: str  # base64 encoded
    sample_rate: int = 48000

# Device listing endpoint
@app.get("/asr/devices")
async def get_audio_devices():
    """List available audio input and output devices"""
    try:
        devices = recorder.list_devices()
        return {
            "status": "success",
            "devices": devices
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Recording control endpoints
@app.post("/asr/start")
async def start_recording(request: StartRecordingRequest, background_tasks: BackgroundTasks):
    """Start stereo audio recording"""
    global is_recording
    
    if is_recording:
        raise HTTPException(status_code=400, detail="Already recording")
    
    try:
        # Set device IDs if provided
        if request.mic_device_id is not None:
            recorder.mic_device = request.mic_device_id
        if request.loopback_device_id is not None:
            recorder.loopback_device = request.loopback_device_id
        
        # Start recording
        success = await recorder.start(request.output_path)
        
        if success:
            is_recording = True
            
            # Setup audio chunk callback to feed transcriber
            def audio_callback(chunk_data):
                if is_transcribing and streamer.streaming:
                    streamer.add_audio_chunk(chunk_data)
            
            recorder.set_chunk_callback(audio_callback)
            
            logger.info("Recording started successfully")
            return {
                "status": "success", 
                "message": "Recording started",
                "output_path": recorder.output_path
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start recording")
            
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/asr/stop") 
async def stop_recording():
    """Stop audio recording"""
    global is_recording
    
    if not is_recording:
        raise HTTPException(status_code=400, detail="Not currently recording")
    
    try:
        output_path = await recorder.stop()
        is_recording = False
        
        logger.info(f"Recording stopped, saved to: {output_path}")
        return {
            "status": "success",
            "message": "Recording stopped",
            "output_path": output_path
        }
        
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Live transcription WebSocket
@app.websocket("/asr/live")
async def websocket_live_transcription(websocket: WebSocket):
    """WebSocket endpoint for live transcription results"""
    await websocket.accept()
    active_connections.append(websocket)
    
    global is_transcribing
    
    try:
        # Start transcription streaming if not already started
        if not is_transcribing:
            def transcription_callback(result: Dict):
                # Broadcast to all connected clients
                message = {
                    "type": "transcription",
                    "data": {
                        "text": result.get("text", ""),
                        "channel": result.get("channel", "mixed"),
                        "timestamp": result.get("timestamp", time.time()),
                        "confidence": result.get("confidence", 0.0)
                    }
                }
                
                # Send to all active connections
                for connection in active_connections[:]:  # Copy list to avoid modification during iteration
                    try:
                        asyncio.create_task(connection.send_text(json.dumps(message)))
                    except:
                        # Remove dead connections
                        if connection in active_connections:
                            active_connections.remove(connection)
            
            if streamer.is_ready():
                success = streamer.start_streaming(transcription_callback)
                if success:
                    is_transcribing = True
                    logger.info("Live transcription started")
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (could be ping/pong or configuration)
                message = await websocket.receive_text()
                # Handle any client messages if needed
                logger.debug(f"Received message: {message}")
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        if websocket in active_connections:
            active_connections.remove(websocket)
        
        # Stop transcription if no more connections
        if not active_connections and is_transcribing:
            streamer.stop_streaming()
            is_transcribing = False
            logger.info("Live transcription stopped - no active connections")

# Single chunk transcription endpoint
@app.post("/asr/transcribe_chunk")
async def transcribe_audio_chunk(request: TranscribeChunkRequest):
    """Transcribe a single audio chunk"""
    try:
        import base64
        
        # Decode base64 audio data
        audio_bytes = base64.b64decode(request.audio_data)
        
        # Transcribe using Whisper
        result = streamer.transcribe_chunk_sync(audio_bytes, request.sample_rate)
        
        if result:
            return {
                "status": "success",
                "transcription": result
            }
        else:
            return {
                "status": "success",
                "transcription": {
                    "text": "",
                    "confidence": 0.0,
                    "has_voice": False
                }
            }
            
    except Exception as e:
        logger.error(f"Error transcribing chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    model_ready = streamer.is_ready()
    return {
        "status": "healthy",
        "service": "asr", 
        "whisper_model_ready": model_ready,
        "recording": is_recording,
        "transcribing": is_transcribing,
        "active_connections": len(active_connections)
    }
"""
Transcription chunk tests for ASR service
"""

import pytest
import requests
import base64
import numpy as np
import json
from fastapi.testclient import TestClient
from services.asr.app import app

ASR_BASE_URL = "http://127.0.0.1:7035"

def generate_test_audio(duration=2.0, sample_rate=48000, frequency=440):
    """Generate test audio data (sine wave)"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Generate a 440Hz sine wave (A note)
    audio = np.sin(2 * np.pi * frequency * t)
    # Convert to 16-bit PCM
    audio_pcm = (audio * 32767).astype(np.int16)
    return audio_pcm.tobytes()

def test_transcribe_chunk_endpoint_structure():
    """Test transcribe_chunk endpoint accepts proper request format"""
    client = TestClient(app)
    
    # Generate test audio
    audio_bytes = generate_test_audio(duration=1.0)
    audio_b64 = base64.b64encode(audio_bytes).decode()
    
    request_data = {
        "audio_data": audio_b64,
        "sample_rate": 48000
    }
    
    response = client.post("/asr/transcribe_chunk", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "transcription" in data

def test_transcribe_chunk_live_service():
    """Test transcribe_chunk endpoint with live service"""
    try:
        # Generate test audio (silence - should not transcribe)
        audio_bytes = b"\\x00" * (48000 * 2)  # 1 second of silence
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        request_data = {
            "audio_data": audio_b64,
            "sample_rate": 48000
        }
        
        response = requests.post(
            f"{ASR_BASE_URL}/asr/transcribe_chunk", 
            json=request_data,
            timeout=10
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "transcription" in data
        
        transcription = data["transcription"]
        # For silence, should return empty text or low confidence
        assert "text" in transcription
        assert "confidence" in transcription
        
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Live ASR service not available: {e}")

def test_invalid_audio_data():
    """Test handling of invalid audio data"""
    client = TestClient(app)
    
    request_data = {
        "audio_data": "invalid_base64_data",
        "sample_rate": 48000
    }
    
    response = client.post("/asr/transcribe_chunk", json=request_data)
    assert response.status_code == 500  # Should fail with invalid data

def test_missing_fields():
    """Test handling of missing required fields"""
    client = TestClient(app)
    
    # Missing audio_data
    response = client.post("/asr/transcribe_chunk", json={"sample_rate": 48000})
    assert response.status_code == 422  # Validation error
    
    # Missing sample_rate (should use default)
    audio_bytes = generate_test_audio(duration=0.5)
    audio_b64 = base64.b64encode(audio_bytes).decode()
    
    response = client.post("/asr/transcribe_chunk", json={"audio_data": audio_b64})
    assert response.status_code == 200  # Should succeed with default sample_rate

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
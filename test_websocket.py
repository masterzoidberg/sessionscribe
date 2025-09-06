"""
Simple WebSocket client test for live transcription
"""

import asyncio
import websockets
import json

async def test_live_transcription():
    """Test live transcription WebSocket endpoint"""
    uri = "ws://127.0.0.1:7035/asr/live"
    
    try:
        print("Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("Connected to live transcription WebSocket")
            
            # Keep connection alive and listen for messages
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data.get("type") == "transcription":
                        transcription_data = data.get("data", {})
                        text = transcription_data.get("text", "")
                        channel = transcription_data.get("channel", "unknown")
                        confidence = transcription_data.get("confidence", 0.0)
                        timestamp = transcription_data.get("timestamp", 0)
                        
                        print(f"[{channel}] {text} (confidence: {confidence:.2f})")
                    
            except asyncio.TimeoutError:
                print("No messages received in 5 seconds")
            except KeyboardInterrupt:
                print("\nStopping test...")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"WebSocket connection closed: {e}")
    except Exception as e:
        print(f"Error connecting to WebSocket: {e}")

async def test_websocket_with_recording():
    """Test WebSocket while recording"""
    import requests
    
    # Start recording first
    try:
        print("Starting recording...")
        start_response = requests.post(
            "http://127.0.0.1:7035/asr/start",
            json={"mic_device_id": 23, "loopback_device_id": 19},
            timeout=5
        )
        
        if start_response.status_code == 200:
            print("Recording started successfully")
            
            # Now test WebSocket
            await test_live_transcription()
            
            # Stop recording
            print("Stopping recording...")
            stop_response = requests.post("http://127.0.0.1:7035/asr/stop", timeout=5)
            if stop_response.status_code == 200:
                result = stop_response.json()
                print(f"Recording stopped: {result.get('output_path')}")
            else:
                print(f"Failed to stop recording: {stop_response.status_code}")
        else:
            print(f"Failed to start recording: {start_response.status_code}")
            print("Trying WebSocket without recording...")
            await test_live_transcription()
            
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        print("Trying WebSocket without recording...")
        await test_live_transcription()

if __name__ == "__main__":
    print("Testing SessionScribe Live Transcription WebSocket")
    print("Make sure to speak into your microphone to test transcription!")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(test_websocket_with_recording())
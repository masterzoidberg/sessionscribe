import asyncio
import numpy as np
import sounddevice as sd
import wave
import threading
import queue
import time
import logging
from typing import Optional, Callable, Dict, List
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WASAPIRecorder:
    def __init__(self, mic_device: Optional[int] = None, loopback_device: Optional[int] = None):
        self.mic_device = mic_device
        self.loopback_device = loopback_device
        self.sample_rate = 48000
        self.channels = 2  # Stereo: L=Therapist(Mic), R=Client(Loopback)
        self.dtype = np.int16
        self.chunk_duration = 1.0  # 1 second chunks
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        
        self.recording = False
        self.output_path: Optional[str] = None
        self.wav_file: Optional[wave.Wave_write] = None
        self.audio_buffer = []
        
        self.mic_stream: Optional[sd.InputStream] = None
        self.loopback_stream: Optional[sd.InputStream] = None
        
        self.chunk_callback: Optional[Callable] = None
        self.rms_callback: Optional[Callable] = None
        self.audio_queue = queue.Queue()
        
        # Audio data accumulation
        self.mic_buffer = []
        self.loopback_buffer = []
        self.buffer_lock = threading.Lock()

    def list_devices(self) -> Dict[str, List[Dict]]:
        """List available audio devices with default selection"""
        try:
            devices = sd.query_devices()
            
            input_devices = []
            output_devices = []
            
            for i, device in enumerate(devices):
                device_info = {
                    "id": i,
                    "name": device['name'],
                    "channels": max(device['max_input_channels'], device['max_output_channels']),
                    "sample_rate": device['default_samplerate']
                }
                
                if device['max_input_channels'] > 0:
                    input_devices.append(device_info)
                if device['max_output_channels'] > 0:
                    output_devices.append(device_info)
            
            # Find defaults
            default_input = None
            default_output = None
            
            for device in input_devices:
                if "microphone" in device['name'].lower() or "mic" in device['name'].lower():
                    default_input = device['id']
                    break
            if not default_input and input_devices:
                default_input = input_devices[0]['id']
                
            for device in output_devices:
                if "speakers" in device['name'].lower() or "headphones" in device['name'].lower():
                    default_output = device['id']
                    break  
            if not default_output and output_devices:
                default_output = output_devices[0]['id']
            
            return {
                "input_devices": input_devices,
                "output_devices": output_devices,
                "default_input": default_input,
                "default_output": default_output
            }
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {"input_devices": [], "output_devices": [], "default_input": None, "default_output": None}

    async def start(self, output_dir: Optional[str] = None):
        if self.recording:
            return False
        
        try:
            self.recording = True
            
            # Setup output file
            if output_dir is None:
                output_dir = os.environ.get('SS_OUTPUT_DIR', 
                                          os.path.join(os.path.expanduser('~'), 'Documents', 'SessionScribe'))
            
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path = os.path.join(output_dir, f"session_{timestamp}_audio.wav")
            
            # Initialize WAV file for stereo recording
            self.wav_file = wave.open(self.output_path, 'wb')
            self.wav_file.setnchannels(self.channels)
            self.wav_file.setsampwidth(2)  # 16-bit
            self.wav_file.setframerate(self.sample_rate)
            
            # Clear buffers
            with self.buffer_lock:
                self.mic_buffer.clear()
                self.loopback_buffer.clear()
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            # Auto-select devices if not set
            if self.mic_device is None or self.loopback_device is None:
                devices = self.list_devices()
                if self.mic_device is None:
                    self.mic_device = devices['default_input']
                if self.loopback_device is None:
                    self.loopback_device = devices['default_output']
            
            # Start recording streams
            await self._start_streams()
            logger.info(f"Started recording: mic={self.mic_device}, loopback={self.loopback_device}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.recording = False
            return False

    async def _start_streams(self):
        """Start both microphone and loopback audio streams"""
        
        def mic_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Mic audio status: {status}")
            
            if self.recording and len(indata) > 0:
                with self.buffer_lock:
                    # Convert to int16 and add to mic buffer  
                    mic_data = (indata[:, 0] * 32767).astype(self.dtype)
                    self.mic_buffer.extend(mic_data)
                    self._process_buffers()
        
        def loopback_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Loopback audio status: {status}")
                
            if self.recording and len(indata) > 0:
                with self.buffer_lock:
                    # For now, simulate loopback with silence or secondary input
                    # Real WASAPI loopback requires pywin32/Windows-specific code
                    try:
                        loopback_data = (indata[:, 0] * 32767).astype(self.dtype)
                    except:
                        loopback_data = np.zeros(len(indata), dtype=self.dtype)
                    self.loopback_buffer.extend(loopback_data)
                    self._process_buffers()

        # Start microphone stream
        self.mic_stream = sd.InputStream(
            device=self.mic_device,
            channels=1,
            samplerate=self.sample_rate,
            dtype=np.float32,
            callback=mic_callback,
            blocksize=1024
        )
        
        # Start loopback stream (using output device as input for simulation)
        try:
            self.loopback_stream = sd.InputStream(
                device=self.loopback_device,
                channels=1,
                samplerate=self.sample_rate,
                dtype=np.float32,
                callback=loopback_callback,
                blocksize=1024
            )
            self.loopback_stream.start()
        except Exception as e:
            logger.warning(f"Could not start loopback stream: {e}, using silence")
            self.loopback_stream = None
        
        self.mic_stream.start()
    
    def _process_buffers(self):
        """Process accumulated audio buffers into chunks"""
        # Check if we have enough data for a chunk (1 second)
        min_samples = min(len(self.mic_buffer), len(self.loopback_buffer))
        
        if min_samples >= self.chunk_size:
            # Extract chunk data
            mic_chunk = np.array(self.mic_buffer[:self.chunk_size])
            loop_chunk = np.array(self.loopback_buffer[:self.chunk_size]) if self.loopback_buffer else np.zeros(self.chunk_size, dtype=self.dtype)
            
            # Remove processed data
            self.mic_buffer = self.mic_buffer[self.chunk_size:]
            if self.loopback_buffer:
                self.loopback_buffer = self.loopback_buffer[self.chunk_size:]
            
            # Create stereo frame: L=Mic, R=Loopback
            stereo_chunk = np.column_stack((mic_chunk, loop_chunk))
            
            # Write to WAV file
            if self.wav_file:
                self.wav_file.writeframes(stereo_chunk.tobytes())
            
            # Create mono mix for transcription
            mono_mix = np.mean(stereo_chunk.astype(np.float32), axis=1)
            mono_pcm = (mono_mix * 32767 / np.max(np.abs(mono_mix)) if np.max(np.abs(mono_mix)) > 0 else mono_mix).astype(self.dtype)
            
            # Add to transcription queue
            self.audio_queue.put({
                'audio': mono_pcm.tobytes(),
                'timestamp': time.time(),
                'duration': self.chunk_duration,
                'sample_rate': self.sample_rate
            })
            
            # Calculate RMS for VU meters
            if self.rms_callback:
                mic_rms = float(np.sqrt(np.mean((mic_chunk / 32767.0) ** 2)))
                loop_rms = float(np.sqrt(np.mean((loop_chunk / 32767.0) ** 2)))
                self.rms_callback({
                    'mic_rms': mic_rms,
                    'loopback_rms': loop_rms,
                    'timestamp': time.time()
                })
            
            # Send to transcriber callback
            if self.chunk_callback:
                asyncio.create_task(self.chunk_callback({
                    'audio': mono_pcm.tobytes(),
                    'timestamp': time.time(),
                    'sample_rate': self.sample_rate
                }))

    async def stop(self):
        if not self.recording:
            return self.output_path
        
        try:
            self.recording = False
            
            # Stop streams
            if self.mic_stream:
                self.mic_stream.stop()
                self.mic_stream.close()
                self.mic_stream = None
                
            if self.loopback_stream:
                self.loopback_stream.stop()
                self.loopback_stream.close()
                self.loopback_stream = None
            
            # Close WAV file
            if self.wav_file:
                self.wav_file.close()
                self.wav_file = None
            
            logger.info(f"Recording stopped, saved to: {self.output_path}")
            return self.output_path
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return self.output_path

    def set_chunk_callback(self, callback: Callable):
        """Set callback for audio chunk processing"""
        self.chunk_callback = callback
        
    def set_rms_callback(self, callback: Callable):
        """Set callback for RMS level updates"""
        self.rms_callback = callback

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[Dict]:
        """Get next audio chunk for transcription"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def get_current_rms(self) -> Dict[str, float]:
        """Get current RMS levels for VU meters"""
        if not self.recording:
            return {"mic_rms": 0.0, "loopback_rms": 0.0}
        
        try:
            with self.buffer_lock:
                if len(self.mic_buffer) > 1024:  # Have enough samples
                    mic_samples = np.array(self.mic_buffer[-1024:]) / 32767.0
                    loop_samples = np.array(self.loopback_buffer[-1024:]) / 32767.0 if len(self.loopback_buffer) > 1024 else np.zeros(1024)
                    
                    mic_rms = float(np.sqrt(np.mean(mic_samples ** 2)))
                    loop_rms = float(np.sqrt(np.mean(loop_samples ** 2)))
                    
                    return {"mic_rms": mic_rms, "loopback_rms": loop_rms}
        except Exception as e:
            logger.error(f"Error calculating RMS: {e}")
        
        return {"mic_rms": 0.0, "loopback_rms": 0.0}

# Global recorder instance
recorder = WASAPIRecorder()
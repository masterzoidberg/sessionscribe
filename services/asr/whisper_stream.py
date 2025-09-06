import asyncio
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional, Dict, Any, List, Callable
import threading
import time
import queue
import logging
import webrtcvad
import io
import wave

logger = logging.getLogger(__name__)

class WhisperStreamer:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        self.processing = False
        self.streaming = False
        self.chunk_buffer = []
        self.last_transcription_time = 0
        
        # VAD setup
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(2)  # Moderate aggressiveness
        
        # Streaming components
        self.audio_queue = queue.Queue()
        self.result_callback: Optional[Callable] = None
        self.stream_thread = None
        
        # Initialize model in background
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        try:
            # Try CUDA first, fallback to CPU
            try:
                self.model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                logger.info(f"Whisper model '{self.model_size}' loaded on CUDA")
            except:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info(f"Whisper model '{self.model_size}' loaded on CPU")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
    
    def _detect_voice_activity(self, audio_bytes: bytes, sample_rate: int = 48000) -> bool:
        """Detect voice activity using WebRTC VAD"""
        try:
            # Convert to numpy array
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Resample to 16kHz for VAD if needed
            if sample_rate != 16000:
                # Simple resampling
                ratio = sample_rate / 16000
                indices = np.arange(0, len(audio_np), ratio).astype(int)
                indices = indices[indices < len(audio_np)]
                audio_np = audio_np[indices]
            
            # VAD requires 20ms frames at 16kHz
            frame_length = 320  # 20ms * 16000Hz / 1000
            
            if len(audio_np) < frame_length:
                return False
            
            # Check multiple frames
            voice_frames = 0
            total_frames = 0
            
            for i in range(0, len(audio_np) - frame_length, frame_length):
                frame = audio_np[i:i + frame_length]
                frame_bytes = frame.astype(np.int16).tobytes()
                
                try:
                    if self.vad.is_speech(frame_bytes, 16000):
                        voice_frames += 1
                    total_frames += 1
                except:
                    continue
            
            # Consider speech if >30% frames have voice
            return total_frames > 0 and (voice_frames / total_frames) > 0.3
            
        except Exception as e:
            logger.warning(f"VAD error: {e}")
            return True  # Default to processing
    
    def _create_wav_buffer(self, audio_data: np.ndarray, sample_rate: int = 48000) -> io.BytesIO:
        """Create WAV buffer for Whisper"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.astype(np.int16).tobytes())
        wav_buffer.seek(0)
        return wav_buffer
        
    def _streaming_loop(self):
        """Continuous processing loop for streaming transcription"""
        logger.info("Starting Whisper streaming loop")
        
        while self.streaming:
            try:
                # Get audio chunk with timeout
                chunk_data = self.audio_queue.get(timeout=1.0)
                
                if chunk_data is None:  # Shutdown signal
                    break
                
                # Extract audio data
                audio_bytes = chunk_data.get('audio')
                sample_rate = chunk_data.get('sample_rate', 48000)
                timestamp = chunk_data.get('timestamp', time.time())
                
                if not audio_bytes:
                    continue
                
                # Voice activity detection
                has_voice = self._detect_voice_activity(audio_bytes, sample_rate)
                if not has_voice:
                    continue
                
                # Convert to numpy and transcribe
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                
                if len(audio_np) > 0:
                    result = self._transcribe_chunk_sync(audio_np, sample_rate)
                    if result and self.result_callback:
                        result['timestamp'] = timestamp
                        self.result_callback(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.streaming:
                    logger.error(f"Error in streaming loop: {e}")
        
        logger.info("Whisper streaming loop ended")
    
    def _transcribe_chunk_sync(self, audio_data: np.ndarray, sample_rate: int = 48000) -> Optional[Dict]:
        """Synchronously transcribe audio chunk"""
        if not self.model:
            return None
            
        try:
            # Convert to float32 for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_float,
                language="en",
                task="transcribe",
                vad_filter=True,
                beam_size=1,
                best_of=1,
                temperature=0.0
            )
            
            # Collect results
            text_parts = []
            for segment in segments:
                if segment.text.strip():
                    text_parts.append(segment.text.strip())
            
            if text_parts:
                full_text = " ".join(text_parts)
                return {
                    "text": full_text,
                    "channel": "mixed",  # For now, mixed audio
                    "confidence": info.language_probability if info else 0.0,
                    "processing_time": 0.0  # Could add timing if needed
                }
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        
        return None

    async def process_chunk(self, audio_data: np.ndarray) -> Optional[Dict[str, Any]]:
        if not self.model or self.processing:
            return None
        
        self.processing = True
        current_time = time.time()
        
        try:
            # Convert stereo to mono for Whisper (mix both channels)
            if len(audio_data.shape) == 2 and audio_data.shape[1] == 2:
                # Separate channels for individual processing
                left_channel = audio_data[:, 0]  # Therapist (Mic)
                right_channel = audio_data[:, 1]  # Client (Loopback)
                
                # Process each channel separately
                results = []
                
                # Process left channel (Therapist)
                if np.any(left_channel):
                    left_float = left_channel.astype(np.float32) / 32768.0
                    left_result = await self._transcribe_audio(left_float, "therapist")
                    if left_result:
                        results.append(left_result)
                
                # Process right channel (Client) 
                if np.any(right_channel):
                    right_float = right_channel.astype(np.float32) / 32768.0
                    right_result = await self._transcribe_audio(right_float, "client")
                    if right_result:
                        results.append(right_result)
                
                if results:
                    return {"transcriptions": results, "timestamp": current_time}
            
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
        finally:
            self.processing = False
        
        return None

    async def _transcribe_audio(self, audio_float: np.ndarray, channel: str) -> Optional[Dict[str, Any]]:
        if len(audio_float) < 1600:  # Minimum 0.1 seconds at 16kHz
            return None
        
        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(audio_float, vad_filter=True, word_timestamps=True)
            )
            
            # Extract transcription results
            for segment in segments:
                if segment.text.strip():
                    return {
                        "channel": channel,
                        "text": segment.text.strip(),
                        "t0": segment.start,
                        "t1": segment.end,
                        "confidence": getattr(segment, 'avg_logprob', 0.0)
                    }
        
        except Exception as e:
            print(f"Error in transcription for {channel}: {e}")
        
        return None

    def start_streaming(self, result_callback: Callable) -> bool:
        """Start streaming transcription"""
        if self.streaming or not self.model:
            return False
        
        try:
            self.streaming = True
            self.result_callback = result_callback
            
            # Clear queue
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            # Start streaming thread
            self.stream_thread = threading.Thread(target=self._streaming_loop)
            self.stream_thread.start()
            
            logger.info("Whisper streaming started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            self.streaming = False
            return False
    
    def stop_streaming(self):
        """Stop streaming transcription"""
        if not self.streaming:
            return
        
        try:
            self.streaming = False
            
            # Send shutdown signal
            self.audio_queue.put(None)
            
            # Wait for thread to finish
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=3.0)
            
            logger.info("Whisper streaming stopped")
            
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
    
    def add_audio_chunk(self, chunk_data: Dict):
        """Add audio chunk to streaming queue"""
        if self.streaming:
            try:
                self.audio_queue.put(chunk_data, timeout=0.1)
            except queue.Full:
                logger.warning("Audio queue full, dropping chunk")
    
    def transcribe_chunk_sync(self, audio_bytes: bytes, sample_rate: int = 48000) -> Optional[Dict]:
        """Synchronously transcribe a single chunk"""
        if not self.model:
            return None
        
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        return self._transcribe_chunk_sync(audio_np, sample_rate)

    def is_ready(self) -> bool:
        return self.model is not None

# Global streamer instance
streamer = WhisperStreamer()
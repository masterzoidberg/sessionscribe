import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Play, Pause, Settings } from 'lucide-react';

interface RecorderProps {
  onSessionUpdate: (data: any) => void;
}

interface AudioDevice {
  id: string;
  name: string;
}

const Recorder: React.FC<RecorderProps> = ({ onSessionUpdate }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [micDevices, setMicDevices] = useState<AudioDevice[]>([]);
  const [selectedMicDevice, setSelectedMicDevice] = useState<string>('');
  const [micLevel, setMicLevel] = useState(0);
  const [loopbackLevel, setLoopbackLevel] = useState(0);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Load available audio devices
    loadAudioDevices();
    
    // Setup keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.altKey && e.key === 'r') {
        e.preventDefault();
        if (isRecording) {
          handleStopRecording();
        } else {
          handleStartRecording();
        }
      }
      
      if (e.ctrlKey && e.altKey && e.key === 'm') {
        e.preventDefault();
        // Mark/bookmark current time
        console.log(`Marked at ${formatTime(recordingTime)}`);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isRecording, recordingTime]);

  const loadAudioDevices = async () => {
    try {
      // In a real implementation, this would query audio devices
      // For now, using mock data
      const devices: AudioDevice[] = [
        { id: 'default', name: 'Default Microphone' },
        { id: 'mic1', name: 'USB Microphone' },
        { id: 'mic2', name: 'Headset Microphone' }
      ];
      setMicDevices(devices);
      if (devices.length > 0) {
        setSelectedMicDevice(devices[0].id);
      }
    } catch (error) {
      console.error('Error loading audio devices:', error);
    }
  };

  const connectWebSocket = () => {
    if (wsRef.current) return;

    wsRef.current = new WebSocket('ws://localhost:7031/transcribe');
    
    wsRef.current.onopen = () => {
      console.log('Connected to transcription service');
    };
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcription') {
        // Forward transcription data to parent or transcription component
        onSessionUpdate(data);
      }
    };
    
    wsRef.current.onclose = () => {
      console.log('Disconnected from transcription service');
      wsRef.current = null;
    };
  };

  const handleStartRecording = async () => {
    try {
      // Connect to transcription service
      connectWebSocket();
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 100));
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        // Send start command with device configuration
        wsRef.current.send(JSON.stringify({
          type: 'start',
          config: {
            mic_device: selectedMicDevice,
            loopback_device: 'default'
          }
        }));
        
        setIsRecording(true);
        setRecordingTime(0);
        
        // Start timer
        intervalRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1);
        }, 1000);
        
        // Simulate audio levels (in real app, these would come from audio analysis)
        simulateAudioLevels();
      }
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const handleStopRecording = async () => {
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      }
      
      setIsRecording(false);
      setIsPaused(false);
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      // Save session data
      const sessionData = {
        duration: recordingTime,
        timestamp: new Date().toISOString()
      };
      onSessionUpdate(sessionData);
      
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    // In real implementation, pause/resume audio recording
  };

  const simulateAudioLevels = () => {
    // Simulate audio level meters
    const updateLevels = () => {
      if (isRecording && !isPaused) {
        setMicLevel(Math.random() * 100);
        setLoopbackLevel(Math.random() * 100);
        setTimeout(updateLevels, 100);
      }
    };
    updateLevels();
  };

  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <h2 className="text-xl font-semibold mb-4">Audio Recording</h2>
        
        {/* Device Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Microphone Device
          </label>
          <select
            value={selectedMicDevice}
            onChange={(e) => setSelectedMicDevice(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isRecording}
          >
            {micDevices.map(device => (
              <option key={device.id} value={device.id}>
                {device.name}
              </option>
            ))}
          </select>
        </div>

        {/* Audio Levels */}
        <div className="mb-6">
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Therapist (Mic)</span>
                <span>{micLevel.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-500 h-2 rounded-full transition-all duration-100"
                  style={{ width: `${micLevel}%` }}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Client (Loopback)</span>
                <span>{loopbackLevel.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-100"
                  style={{ width: `${loopbackLevel}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Recording Controls */}
        <div className="flex items-center justify-between">
          <div className="flex space-x-4">
            {!isRecording ? (
              <button
                onClick={handleStartRecording}
                className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                <Mic className="h-5 w-5" />
                <span>Start Recording</span>
              </button>
            ) : (
              <>
                <button
                  onClick={handleStopRecording}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  <Square className="h-5 w-5" />
                  <span>Stop</span>
                </button>
                
                <button
                  onClick={handlePauseResume}
                  className="flex items-center space-x-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                >
                  {isPaused ? <Play className="h-5 w-5" /> : <Pause className="h-5 w-5" />}
                  <span>{isPaused ? 'Resume' : 'Pause'}</span>
                </button>
              </>
            )}
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-mono font-bold text-gray-900">
              {formatTime(recordingTime)}
            </div>
            <div className="text-sm text-gray-500">
              {isRecording && (
                <>
                  <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse mr-2"></span>
                  {isPaused ? 'PAUSED' : 'RECORDING'}
                </>
              )}
            </div>
          </div>
        </div>
        
        {/* Hotkeys Info */}
        <div className="mt-4 text-sm text-gray-500 border-t pt-4">
          <p><strong>Hotkeys:</strong> Ctrl+Alt+R (Start/Stop) • Ctrl+Alt+M (Mark)</p>
        </div>
      </div>
    </div>
  );
};

export default Recorder;
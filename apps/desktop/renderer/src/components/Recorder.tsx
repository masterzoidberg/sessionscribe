import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Play, Pause } from 'lucide-react';

interface AudioDevice {
  id: number;
  name: string;
  hostApi: string;
  type: 'input' | 'output';
}

const Recorder: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [micDevices, setMicDevices] = useState<AudioDevice[]>([]);
  const [loopbackDevices, setLoopbackDevices] = useState<AudioDevice[]>([]);
  const [selectedMicDevice, setSelectedMicDevice] = useState<string>('');
  const [selectedLoopbackDevice, setSelectedLoopbackDevice] = useState<string>('');
  const [micLevel, setMicLevel] = useState(0);
  const [loopbackLevel, setLoopbackLevel] = useState(0);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadAudioDevices();

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
        console.log(`Marked at ${formatTime(recordingTime)}`);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isRecording, recordingTime]);

  const loadAudioDevices = async () => {
    try {
      const devices = await window.electronAPI.record.getAudioDevices();
      const micDevices = devices.filter(d => d.type === 'input');
      const loopbackDevices = devices.filter(d => d.type === 'output' && d.hostApi === 'WASAPI');
      
      setMicDevices(micDevices);
      setLoopbackDevices(loopbackDevices);

      if (micDevices.length > 0) {
        setSelectedMicDevice(micDevices[0].id.toString());
      }
      if (loopbackDevices.length > 0) {
        setSelectedLoopbackDevice(loopbackDevices[0].id.toString());
      }
    } catch (error) {
      console.error('Error loading audio devices:', error);
    }
  };

  const handleStartRecording = async () => {
    try {
      const result = await window.electronAPI.record.start({
        mic_device_id: parseInt(selectedMicDevice),
        loopback_device_id: parseInt(selectedLoopbackDevice),
      });

      if (result.success) {
        setIsRecording(true);
        setRecordingTime(0);

        intervalRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1);
        }, 1000);

        simulateAudioLevels();
      } else {
        console.error('Failed to start recording');
      }
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const handleStopRecording = async () => {
    try {
      const result = await window.electronAPI.record.stop();
      if (result.success) {
        setIsRecording(false);
        setIsPaused(false);

        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } else {
        console.error('Failed to stop recording');
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
  };

  const simulateAudioLevels = () => {
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

        <div className="grid grid-cols-2 gap-6 mb-6">
          <div>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Loopback Device (WASAPI)
            </label>
            <select
              value={selectedLoopbackDevice}
              onChange={(e) => setSelectedLoopbackDevice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isRecording}
            >
              {loopbackDevices.map(device => (
                <option key={device.id} value={device.id}>
                  {device.name}
                </option>
              ))}
            </select>
          </div>
        </div>

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

        <div className="mt-4 text-sm text-gray-500 border-t pt-4">
          <p><strong>Hotkeys:</strong> Ctrl+Alt+R (Start/Stop) • Ctrl+Alt+M (Mark)</p>
        </div>
      </div>
    </div>
  );
};

export default Recorder;

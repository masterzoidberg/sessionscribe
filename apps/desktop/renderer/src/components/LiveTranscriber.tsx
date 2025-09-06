import React, { useState, useEffect, useRef } from 'react';
import { Copy, Download, Clock } from 'lucide-react';

interface Transcription {
  channel: 'therapist' | 'client';
  text: string;
  t0: number;
  t1: number;
  confidence?: number;
  timestamp: number;
}

const LiveTranscriber: React.FC = () => {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [viewMode, setViewMode] = useState<'lanes' | 'unified'>('lanes');
  const [latencyMetrics, setLatencyMetrics] = useState({
    p95: 0,
    avg: 0,
    count: 0
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const latencyBuffer = useRef<number[]>([]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcriptions]);

  useEffect(() => {
    connectToService();

    const handleTranscriptionData = (_event: any, data: string) => {
      const parsedData = JSON.parse(data);
      if (parsedData.type === 'transcription' && parsedData.data?.text) {
        const now = Date.now();
        const latency = (now - parsedData.data.timestamp) / 1000;
        addTranscription({
          ...parsedData.data,
          timestamp: parsedData.data.timestamp
        });
        updateLatencyMetrics(latency);
      }
    };

    window.electronAPI.transcription.onData(handleTranscriptionData);

    return () => {
      window.electronAPI.transcription.disconnect();
    };
  }, []);

  const connectToService = async () => {
    try {
      await window.electronAPI.transcription.connect();
      setIsConnected(true);
      console.log('Connected to transcription service');
    } catch (error) {
      console.error('Error connecting to transcription service:', error);
      setIsConnected(false);
    }
  };

  const addTranscription = (transcription: Transcription) => {
    setTranscriptions(prev => [...prev, transcription]);
  };

  const updateLatencyMetrics = (latency: number) => {
    latencyBuffer.current.push(latency);

    if (latencyBuffer.current.length > 100) {
      latencyBuffer.current.shift();
    }

    const sorted = [...latencyBuffer.current].sort((a, b) => a - b);
    const p95Index = Math.floor(sorted.length * 0.95);
    const p95 = sorted[p95Index] || 0;
    const avg = sorted.reduce((sum, val) => sum + val, 0) / sorted.length;

    setLatencyMetrics({
      p95: p95,
      avg: avg,
      count: sorted.length
    });
  };

  const copyTranscription = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const copyAllTranscriptions = () => {
    const allText = transcriptions.map(t =>
      `[${t.channel.toUpperCase()}] ${t.text}`
    ).join('\n');
    navigator.clipboard.writeText(allText);
  };

  const downloadTranscriptions = () => {
    const content = transcriptions.map(t =>
      `[${formatTime(t.t0)} - ${formatTime(t.t1)}] [${t.channel.toUpperCase()}] ${t.text}`
    ).join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcription_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
  };

  const getChannelColor = (channel: string) => {
    return channel === 'therapist' ? 'bg-green-50 border-green-200' : 'bg-blue-50 border-blue-200';
  };

  const getChannelIcon = (channel: string) => {
    return channel === 'therapist' ? 'T' : 'C';
  };

  const renderLanesView = () => {
    const therapistTranscriptions = transcriptions.filter(t => t.channel === 'therapist');
    const clientTranscriptions = transcriptions.filter(t => t.channel === 'client');

    return (
      <div className="grid grid-cols-2 gap-4 h-full">
        {/* Therapist Lane */}
        <div className="flex flex-col">
          <div className="bg-green-100 p-2 text-center font-semibold text-green-800">
            Therapist (Mic)
          </div>
          <div className="flex-1 overflow-y-auto space-y-2 p-2">
            {therapistTranscriptions.map((t, index) => (
              <div key={index} className="bg-green-50 border border-green-200 rounded p-2">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs text-green-600">
                    {formatTime(t.t0)} - {formatTime(t.t1)}
                  </span>
                  <button
                    onClick={() => copyTranscription(t.text)}
                    className="text-green-600 hover:text-green-800"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
                <p className="text-sm text-gray-900">{t.text}</p>
                {t.confidence && (
                  <div className="text-xs text-green-600 mt-1">
                    Confidence: {(t.confidence * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Client Lane */}
        <div className="flex flex-col">
          <div className="bg-blue-100 p-2 text-center font-semibold text-blue-800">
            Client (Loopback)
          </div>
          <div className="flex-1 overflow-y-auto space-y-2 p-2">
            {clientTranscriptions.map((t, index) => (
              <div key={index} className="bg-blue-50 border border-blue-200 rounded p-2">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs text-blue-600">
                    {formatTime(t.t0)} - {formatTime(t.t1)}
                  </span>
                  <button
                    onClick={() => copyTranscription(t.text)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
                <p className="text-sm text-gray-900">{t.text}</p>
                {t.confidence && (
                  <div className="text-xs text-blue-600 mt-1">
                    Confidence: {(t.confidence * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderUnifiedView = () => {
    return (
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 p-4">
        {transcriptions.map((t, index) => (
          <div key={index} className={`border rounded p-3 ${getChannelColor(t.channel)}`}>
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center space-x-2">
                <span className={`inline-block w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${ 
                  t.channel === 'therapist' ? 'bg-green-500 text-white' : 'bg-blue-500 text-white'
                }`}>
                  {getChannelIcon(t.channel)}
                </span>
                <span className="text-xs text-gray-600">
                  {formatTime(t.t0)} - {formatTime(t.t1)}
                </span>
              </div>
              <button
                onClick={() => copyTranscription(t.text)}
                className="text-gray-500 hover:text-gray-700"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
            <p className="text-sm text-gray-900">{t.text}</p>
            {t.confidence && (
              <div className="text-xs text-gray-600 mt-1">
                Confidence: {(t.confidence * 100).toFixed(0)}%
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Live Transcription</h2>

          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${ 
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="text-xs text-gray-600">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Latency Metrics */}
            <div className="flex items-center space-x-1 text-xs text-gray-600">
              <Clock className="h-3 w-3" />
              <span>P95: {latencyMetrics.p95.toFixed(2)}s</span>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex justify-between items-center">
          <div className="flex space-x-2">
            <button
              onClick={() => setViewMode('lanes')}
              className={`px-3 py-1 text-xs rounded ${ 
                viewMode === 'lanes' ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              Two Lanes
            </button>
            <button
              onClick={() => setViewMode('unified')}
              className={`px-3 py-1 text-xs rounded ${ 
                viewMode === 'unified' ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              Unified
            </button>
          </div>

          <div className="flex space-x-2">
            <button
              onClick={copyAllTranscriptions}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
            >
              <Copy className="h-3 w-3" />
              <span>Copy All</span>
            </button>
            <button
              onClick={downloadTranscriptions}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
            >
              <Download className="h-3 w-3" />
              <span>Download</span>
            </button>
          </div>
        </div>
      </div>

      {/* Transcription Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'lanes' ? renderLanesView() : renderUnifiedView()}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-2 text-xs text-gray-500 text-center">
        {transcriptions.length} transcriptions •
        Avg latency: {latencyMetrics.avg.toFixed(2)}s •
        Target: ≤2.0s p95
      </div>
    </div>
  );
};

export default LiveTranscriber;

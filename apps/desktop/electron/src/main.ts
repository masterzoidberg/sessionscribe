import { app, BrowserWindow, ipcMain, protocol, shell, session } from 'electron';
import * as path from 'path';
import * as os from 'os';
import Store from 'electron-store';
import axios from 'axios';
import WebSocket from 'ws';

// Ensure single instance
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

const store = new Store();
let mainWindow: BrowserWindow | null = null;
let transcriptionSocket: WebSocket | null = null;

// Security: Register file protocol for local output directory
app.whenReady().then(() => {
  protocol.registerFileProtocol('safe-file', (request, callback) => {
    const outputDir = process.env.SS_OUTPUT_DIR || path.join(os.homedir(), 'Documents', 'SessionScribe');
    const url = request.url.substr(10); // Remove 'safe-file:'
    const filePath = path.join(outputDir, url);
    
    // Ensure path is within output directory
    if (!filePath.startsWith(outputDir)) {
      callback({ error: -3 }); // ABORTED
      return;
    }
    
    callback({ path: filePath });
  });

  // Security: Add Content Security Policy headers
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self' http://localhost:3001 http://127.0.0.1:3001 ws://localhost:3001 ws://127.0.0.1:3001; " +
          "script-src 'self' 'unsafe-eval' http://localhost:3001 http://127.0.0.1:3001; " +
          "style-src 'self' 'unsafe-inline' http://localhost:3001 http://127.0.0.1:3001; " +
          "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*; " +
          "img-src 'self' data: blob:;"
        ]
      }
    });
  });
});

const createWindow = (): void => {
  const preloadPath = path.join(__dirname, 'preload.js');
  console.log('[main] preload:', preloadPath);
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true, // Enable sandbox for security
      preload: preloadPath,
    },
    show: false,
  });

  // Load renderer
  if (process.env.NODE_ENV === 'development') {
    const rendererPort = process.env.VITE_RENDERER_PORT || '3001';
    mainWindow.loadURL(`http://localhost:${rendererPort}`);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Security: Prevent new window creation
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
};

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

// Quit lifecycle cleanup - stop recordings and services
app.on('before-quit', async (e) => {
  e.preventDefault(); // Prevent immediate quit
  
  try {
    console.log('[main] Stopping services before quit...');
    
    // Stop dual-channel session if active
    if (currentDualChannelSessionId) {
      try {
        await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/stop`, {
          session_id: currentDualChannelSessionId
        }, { timeout: 3000 });
        console.log('[main] Stopped dual-channel session on quit');
      } catch (err) {
        console.warn('[main] Failed to stop dual-channel session on quit:', err.message);
      }
    }
    
    // Stop legacy stream session if active
    if (currentSessionId) {
      try {
        await axios.post(`http://127.0.0.1:${ASR_PORT}/stream/stop`, {
          session_id: currentSessionId
        }, { timeout: 3000 });
        console.log('[main] Stopped ASR stream session on quit');
      } catch (err) {
        console.warn('[main] Failed to stop ASR stream session on quit:', err.message);
      }
    }
    
    // Stop stereo session if active
    if (currentStereoSessionId) {
      try {
        await axios.post(`http://127.0.0.1:${ASR_PORT}/control/stereo/stop`, {
          session_id: currentStereoSessionId
        }, { timeout: 3000 });
        console.log('[main] Stopped stereo session on quit');
      } catch (err) {
        console.warn('[main] Failed to stop stereo session on quit:', err.message);
      }
    }
    
    // Clear intervals
    if (streamingInterval) clearInterval(streamingInterval);
    if (stereoStatusInterval) clearInterval(stereoStatusInterval);
    if (dualChannelStatusInterval) clearInterval(dualChannelStatusInterval);
    
    // Close websocket if open
    if (transcriptionSocket) {
      transcriptionSocket.close();
    }
    
    console.log('[main] Cleanup complete, proceeding with quit');
  } catch (err) {
    console.error('[main] Error during quit cleanup:', err);
  } finally {
    // Allow quit to proceed
    app.exit(0);
  }
});

// Global state for ASR streaming
let currentSessionId: string | null = null;
let streamingInterval: NodeJS.Timeout | null = null;

// Phase 4 Stereo session state
let currentStereoSessionId: string | null = null;
let stereoStatusInterval: NodeJS.Timeout | null = null;

// Dual-channel session state
let currentDualChannelSessionId: string | null = null;
let dualChannelStatusInterval: NodeJS.Timeout | null = null;

// Service ports from environment
const ASR_PORT = process.env.ASR_PORT || '7035';
const REDACTION_PORT = process.env.REDACTION_PORT || '7032';
const INSIGHTS_PORT = process.env.INSIGHTS_PORT || '7033';
const NOTE_BUILDER_PORT = process.env.NOTE_BUILDER_PORT || '7034';

// Ping handler for bridge validation
ipcMain.handle('ping', () => 'pong');

// New bridge API handlers
ipcMain.handle('audio.enumerateDevices', async () => {
  try {
    const response = await axios.get(`http://127.0.0.1:${ASR_PORT}/devices`);
    return response.data;
  } catch (error) {
    console.error('Error getting audio devices:', error);
    return { input_devices: [], output_devices: [], loopback_devices: [], has_loopback: false };
  }
});

ipcMain.handle('asr.startDualChannel', async (_, config) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/start`, {
      sample_rate: config.sample_rate || 44100,
      mic_device_id: config.mic_device_id,
      output_device_id: config.output_device_id,
      buffer_size_ms: config.buffer_size_ms || 100,
      exclusive_mode: config.exclusive_mode || false
    });
    
    currentDualChannelSessionId = response.data.session_id;
    console.log('Started dual-channel ASR session via bridge:', currentDualChannelSessionId);
    
    return { 
      success: true, 
      session_id: currentDualChannelSessionId,
      sample_rate: response.data.sample_rate,
      buffer_size_ms: response.data.buffer_size_ms
    };
  } catch (error) {
    console.error('Error starting dual-channel session via bridge:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('asr.stopDualChannel', async (_, sessionId) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/stop`, {
      session_id: sessionId
    });
    
    if (currentDualChannelSessionId === sessionId) {
      currentDualChannelSessionId = null;
      if (dualChannelStatusInterval) {
        clearInterval(dualChannelStatusInterval);
        dualChannelStatusInterval = null;
      }
    }
    
    console.log('Stopped dual-channel ASR session via bridge:', sessionId);
    return { success: true };
  } catch (error) {
    console.error('Error stopping dual-channel session via bridge:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('transcription.connect', async () => {
  // Safe no-op for compatibility
  console.log('Transcription connection established via bridge (no-op)');
  return Promise.resolve();
});

// Legacy IPC handlers (kept for backward compatibility)
ipcMain.handle('asr:getDevices', async () => {
  try {
    // Return mock devices - real device enumeration handled by renderer WebRTC
    return [
      { id: 0, name: "Default Microphone", type: "input", hostApi: "WASAPI" },
      { id: 1, name: "Default Speakers", type: "output", hostApi: "WASAPI" }
    ];
  } catch (error) {
    console.error('Error getting audio devices:', error);
    return [];
  }
});

ipcMain.handle('asr:startStream', async (_, config) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/stream/start`, {
      sample_rate: config.sample_rate || 48000,
      channels: 2,
      format: "pcm_s16le"
    });
    
    currentSessionId = response.data.session_id;
    console.log('Started ASR stream session:', currentSessionId);
    
    return { success: true, sessionId: currentSessionId };
  } catch (error) {
    console.error('Error starting ASR stream:', error);
    return { success: false };
  }
});

ipcMain.handle('asr:sendChunk', async (_, chunkData) => {
  if (!currentSessionId) {
    return { success: false, error: "No active session" };
  }
  
  try {
    const startTime = Date.now();
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/stream/chunk`, {
      session_id: currentSessionId,
      pcm_chunk_base64: chunkData,
      client_timestamp: startTime
    });
    
    // Forward transcription data to renderer
    if (response.data && mainWindow) {
      const endTime = Date.now();
      const serverLatency = response.data.server_timestamp ? endTime - response.data.server_timestamp : 0;
      const totalLatency = endTime - startTime;
      
      const transcriptionData = {
        type: 'transcription',
        data: {
          text: response.data.partial_text || response.data.final_text || '',
          channel: response.data.channel || 'mixed',
          timestamp: response.data.timestamp || response.data.server_timestamp || endTime,
          confidence: response.data.confidence || 1.0,
          is_final: response.data.is_final || false,
          partial: !response.data.is_final,
          latency: {
            total: totalLatency,
            server: serverLatency,
            client_sent: startTime,
            client_received: endTime
          }
        }
      };
      
      // Only send if there's actual text content
      if (transcriptionData.data.text.trim()) {
        mainWindow.webContents.send('asr:transcriptionData', '_', JSON.stringify(transcriptionData));
      }
      
      // Log latency metrics in development mode
      if (process.env.NODE_ENV === 'development' && transcriptionData.data.text.trim()) {
        console.log(`ASR latency: ${totalLatency}ms (${transcriptionData.data.is_final ? 'final' : 'partial'})`);
      }
    }
    
    return { success: true, partial_text: response.data.partial_text };
  } catch (error) {
    console.error('Error sending audio chunk:', error);
    return { success: false };
  }
});

ipcMain.handle('asr:stopStream', async () => {
  if (!currentSessionId) {
    return { success: false };
  }
  
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/stream/stop`, {
      session_id: currentSessionId
    });
    
    const sessionId = currentSessionId;
    currentSessionId = null;
    
    console.log('Stopped ASR stream session:', sessionId);
    console.log('Final transcript:', response.data.final_text);
    console.log('Audio saved to:', response.data.wav_path);
    
    return { 
      success: true, 
      final_text: response.data.final_text,
      wav_path: response.data.wav_path
    };
  } catch (error) {
    console.error('Error stopping ASR stream:', error);
    currentSessionId = null;
    return { success: false };
  }
});

ipcMain.handle('asr:connect', async () => {
  // Connection is handled per-chunk basis, no persistent connection needed
  console.log('ASR connection established');
});

ipcMain.handle('asr:disconnect', async () => {
  // Clean up any active sessions
  if (currentSessionId) {
    try {
      await axios.post(`http://127.0.0.1:${ASR_PORT}/stream/stop`, {
        session_id: currentSessionId
      });
    } catch (error) {
      console.error('Error cleaning up session on disconnect:', error);
    }
    currentSessionId = null;
  }
  
  // Clean up stereo sessions
  if (currentStereoSessionId) {
    try {
      if (stereoStatusInterval) {
        clearInterval(stereoStatusInterval);
        stereoStatusInterval = null;
      }
      await axios.post(`http://127.0.0.1:${ASR_PORT}/control/stereo/stop`, {
        session_id: currentStereoSessionId
      });
    } catch (error) {
      console.error('Error cleaning up stereo session on disconnect:', error);
    }
    currentStereoSessionId = null;
  }
  
  // Clean up dual-channel sessions
  if (currentDualChannelSessionId) {
    try {
      if (dualChannelStatusInterval) {
        clearInterval(dualChannelStatusInterval);
        dualChannelStatusInterval = null;
      }
      await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/stop`, {
        session_id: currentDualChannelSessionId
      });
    } catch (error) {
      console.error('Error cleaning up dual-channel session on disconnect:', error);
    }
    currentDualChannelSessionId = null;
  }
  
  console.log('ASR connection disconnected');
});

// Phase 4 Stereo IPC handlers
ipcMain.handle('asr:getAudioDevices', async () => {
  try {
    const response = await axios.get(`http://127.0.0.1:${ASR_PORT}/devices`);
    return response.data;
  } catch (error) {
    console.error('Error getting audio devices:', error);
    return { input_devices: [], output_devices: [], loopback_devices: [], has_loopback: false };
  }
});

ipcMain.handle('asr:startStereo', async (_, config) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/control/stereo/start`, {
      sample_rate: config.sample_rate || 48000,
      chunk_ms: config.chunk_ms || 1000,
      vad_enabled: config.vad_enabled ?? true,
      auto_balance: config.auto_balance || "off",
      mic_device: config.mic_device,
      loopback_device: config.loopback_device
    });
    
    currentStereoSessionId = response.data.session_id;
    console.log('Started stereo ASR session:', currentStereoSessionId);
    
    // Start polling for transcription updates
    startStereoTranscriptionPolling();
    
    return { success: true, sessionId: currentStereoSessionId };
  } catch (error) {
    console.error('Error starting stereo session:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('asr:stopStereo', async () => {
  if (!currentStereoSessionId) {
    return { success: false, error: "No active stereo session" };
  }
  
  try {
    // Stop polling
    if (stereoStatusInterval) {
      clearInterval(stereoStatusInterval);
      stereoStatusInterval = null;
    }
    
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/control/stereo/stop`, {
      session_id: currentStereoSessionId
    });
    
    const sessionId = currentStereoSessionId;
    currentStereoSessionId = null;
    
    console.log('Stopped stereo ASR session:', sessionId);
    
    return { 
      success: true, 
      final_transcript: response.data.final_transcript,
      wav_path: response.data.wav_path,
      transcript_path: response.data.transcript_path
    };
  } catch (error) {
    console.error('Error stopping stereo session:', error);
    currentStereoSessionId = null;
    return { success: false, error: error.message };
  }
});

// Function to poll for stereo transcription updates
function startStereoTranscriptionPolling() {
  if (stereoStatusInterval) {
    clearInterval(stereoStatusInterval);
  }
  
  stereoStatusInterval = setInterval(async () => {
    if (!currentStereoSessionId || !mainWindow) {
      return;
    }
    
    try {
      const response = await axios.get(`http://127.0.0.1:${ASR_PORT}/control/stereo/${currentStereoSessionId}/status`);
      
      if (response.data.recent_transcripts) {
        // Send each recent transcript chunk to renderer
        for (const channel of ['L', 'R']) {
          const recentChunks = response.data.recent_transcripts[channel];
          for (const chunk of recentChunks) {
            if (chunk.text && chunk.text.trim()) {
              const transcriptionData = {
                type: 'transcription',
                data: {
                  text: chunk.text,
                  channel: channel === 'L' ? 'therapist' : 'client',
                  timestamp: chunk.timestamp * 1000, // Convert to ms
                  confidence: chunk.confidence || 0.8,
                  is_final: chunk.is_final || true,
                  partial: false,
                  latency: {
                    total: 0, // Will be calculated by renderer
                    server: 0,
                    client_sent: chunk.timestamp * 1000,
                    client_received: Date.now()
                  },
                  rms: chunk.rms || 0,
                  vad: chunk.vad || true
                }
              };
              
              mainWindow.webContents.send('asr:transcriptionData', '_', JSON.stringify(transcriptionData));
            }
          }
        }
      }
    } catch (error) {
      console.error('Error polling stereo status:', error);
    }
  }, 1000); // Poll every 1 second
}

// Dual-Channel IPC handlers
ipcMain.handle('asr:startDualChannel', async (_, config) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/start`, {
      sample_rate: config.sample_rate || 44100,
      mic_device_id: config.mic_device_id,
      output_device_id: config.output_device_id,
      buffer_size_ms: config.buffer_size_ms || 100,
      exclusive_mode: config.exclusive_mode || false
    });
    
    currentDualChannelSessionId = response.data.session_id;
    console.log('Started dual-channel ASR session:', currentDualChannelSessionId);
    
    // Start polling for transcription updates
    startDualChannelTranscriptionPolling();
    
    return { success: true, sessionId: currentDualChannelSessionId };
  } catch (error) {
    console.error('Error starting dual-channel session:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('asr:stopDualChannel', async () => {
  if (!currentDualChannelSessionId) {
    return { success: false, error: "No active dual-channel session" };
  }
  
  try {
    // Stop polling
    if (dualChannelStatusInterval) {
      clearInterval(dualChannelStatusInterval);
      dualChannelStatusInterval = null;
    }
    
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/stop`, {
      session_id: currentDualChannelSessionId
    });
    
    const sessionId = currentDualChannelSessionId;
    currentDualChannelSessionId = null;
    
    console.log('Stopped dual-channel ASR session:', sessionId);
    
    return { 
      success: true, 
      final_transcript: response.data.final_transcript,
      transcript_path: response.data.transcript_path,
      total_chunks_processed: response.data.total_chunks_processed
    };
  } catch (error) {
    console.error('Error stopping dual-channel session:', error);
    currentDualChannelSessionId = null;
    return { success: false, error: error.message };
  }
});

ipcMain.handle('asr:sendDualChannelChunk', async (_, chunkData) => {
  if (!currentDualChannelSessionId) {
    return { success: false, error: "No active dual-channel session" };
  }
  
  try {
    const response = await axios.post(`http://127.0.0.1:${ASR_PORT}/dual-channel/chunk`, {
      session_id: currentDualChannelSessionId,
      channel: chunkData.channel, // "therapist" or "client"
      pcm_chunk_base64: chunkData.pcm_chunk_base64,
      timestamp: chunkData.timestamp || Date.now() / 1000
    });
    
    return { 
      success: true,
      chunks_in_queue: response.data.chunks_in_queue
    };
  } catch (error) {
    console.error('Error sending dual-channel chunk:', error);
    return { success: false, error: error.message };
  }
});

// Function to poll for dual-channel transcription updates
function startDualChannelTranscriptionPolling() {
  if (dualChannelStatusInterval) {
    clearInterval(dualChannelStatusInterval);
  }
  
  dualChannelStatusInterval = setInterval(async () => {
    if (!currentDualChannelSessionId || !mainWindow) {
      return;
    }
    
    try {
      const response = await axios.get(`http://127.0.0.1:${ASR_PORT}/dual-channel/${currentDualChannelSessionId}/status`);
      
      if (response.data.recent_transcripts) {
        // Send each recent transcript chunk to renderer
        for (const channel of ['therapist', 'client']) {
          const recentChunks = response.data.recent_transcripts[channel];
          for (const chunk of recentChunks) {
            if (chunk.text && chunk.text.trim()) {
              const transcriptionData = {
                type: 'transcription',
                data: {
                  text: chunk.text,
                  channel: channel, // Already tagged as "therapist" or "client"
                  timestamp: chunk.timestamp * 1000, // Convert to ms
                  confidence: chunk.confidence || 0.8,
                  is_final: chunk.is_final || true,
                  partial: false,
                  latency: {
                    total: 0, // Will be calculated by renderer
                    server: 0,
                    client_sent: chunk.timestamp * 1000,
                    client_received: Date.now()
                  },
                  source: 'dual-channel' // Mark as dual-channel source
                }
              };
              
              mainWindow.webContents.send('asr:transcriptionData', '_', JSON.stringify(transcriptionData));
            }
          }
        }
      }
    } catch (error) {
      console.error('Error polling dual-channel status:', error);
    }
  }, 500); // Poll every 500ms for more responsive updates
}

ipcMain.handle('settings:get', async (_, key) => {
  return store.get(key);
});

ipcMain.handle('settings:set', async (_, key, value) => {
  store.set(key, value);
  return true;
});

ipcMain.handle('note:save', async (_, noteData, filePath) => {
  // Save note to file system
  return { success: true, path: filePath };
});

ipcMain.handle('dashboard:send', async (_, snapshotId, askFor) => {
  // Send to insights bridge if online and redacted
  return { success: true };
});

// Redaction service IPC handlers
ipcMain.handle('redaction:processText', async (_, text) => {
  try {
    // Ingest text as chunks (simplified for single text input)
    const response = await axios.post(`http://127.0.0.1:${REDACTION_PORT}/redaction/ingest`, {
      text: text,
      channel: 'mixed',
      timestamp: Date.now() / 1000,
      t0: 0,
      t1: text.split(' ').length * 0.5 // Rough estimate
    });
    
    // Run slow detection
    await axios.post(`http://127.0.0.1:${REDACTION_PORT}/redaction/process-slow`);
    
    // Get snapshot
    const snapshotResponse = await axios.get(`http://127.0.0.1:${REDACTION_PORT}/redaction/snapshot`);
    
    return {
      success: true,
      snapshot: snapshotResponse.data
    };
  } catch (error) {
    console.error('Error processing text for redaction:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('redaction:applyRedaction', async (_, snapshotId, acceptedEntityIds) => {
  try {
    const response = await axios.post(`http://127.0.0.1:${REDACTION_PORT}/redaction/apply/${snapshotId}`, acceptedEntityIds);
    
    return {
      success: true,
      redacted_text: response.data.redacted_text,
      entities_applied: response.data.entities_applied
    };
  } catch (error) {
    console.error('Error applying redaction:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('redaction:saveRedactedTranscript', async (_, redactedText, sessionTimestamp) => {
  try {
    const fs = require('fs').promises;
    const path = require('path');
    const os = require('os');
    
    const outputDir = process.env.SS_OUTPUT_DIR || path.join(os.homedir(), 'Documents', 'SessionScribe');
    await fs.mkdir(outputDir, { recursive: true });
    
    const filename = sessionTimestamp || new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + new Date().toISOString().replace(/[:.]/g, '-').split('T')[1].split('.')[0];
    const filePath = path.join(outputDir, `session_${filename}_redacted.txt`);
    
    await fs.writeFile(filePath, redactedText, 'utf-8');
    
    return {
      success: true,
      path: filePath
    };
  } catch (error) {
    console.error('Error saving redacted transcript:', error);
    return { success: false, error: error.message };
  }
});
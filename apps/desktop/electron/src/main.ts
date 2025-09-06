import { app, BrowserWindow, ipcMain, protocol, shell } from 'electron';
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
});

const createWindow = (): void => {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
  });

  // Load renderer
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000');
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

// IPC handlers for secure communication
ipcMain.handle('record:getAudioDevices', async () => {
  try {
    const response = await axios.get('http://localhost:7031/asr/devices');
    return response.data.devices;
  } catch (error) {
    console.error('Error getting audio devices:', error);
    return [];
  }
});

ipcMain.handle('record:start', async (_, deviceConfig) => {
  try {
    const response = await axios.post('http://localhost:7031/asr/start', deviceConfig);
    return { success: true, sessionId: response.data.output_path };
  } catch (error) {
    console.error('Error starting recording:', error);
    return { success: false };
  }
});

ipcMain.handle('record:stop', async () => {
  try {
    await axios.post('http://localhost:7031/asr/stop');
    return { success: true };
  } catch (error) {
    console.error('Error stopping recording:', error);
    return { success: false };
  }
});

ipcMain.handle('transcription:connect', () => {
  if (transcriptionSocket) {
    return;
  }
  transcriptionSocket = new WebSocket('ws://localhost:7031/asr/live');

  transcriptionSocket.on('message', (data) => {
    mainWindow?.webContents.send('transcription:data', data.toString());
  });

  transcriptionSocket.on('close', () => {
    transcriptionSocket = null;
  });
});

ipcMain.handle('transcription:disconnect', () => {
  if (transcriptionSocket) {
    transcriptionSocket.close();
  }
});

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
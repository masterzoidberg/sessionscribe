import { contextBridge, ipcRenderer } from 'electron';

// Expose safe API to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  record: {
    getAudioDevices: () => ipcRenderer.invoke('record:getAudioDevices'),
    start: (deviceConfig: any) => ipcRenderer.invoke('record:start', deviceConfig),
    stop: () => ipcRenderer.invoke('record:stop'),
  },
  transcription: {
    onData: (callback: any) => ipcRenderer.on('transcription:data', callback),
    connect: () => ipcRenderer.invoke('transcription:connect'),
    disconnect: () => ipcRenderer.invoke('transcription:disconnect'),
  },
  settings: {
    get: (key: string) => ipcRenderer.invoke('settings:get', key),
    set: (key: string, value: any) => ipcRenderer.invoke('settings:set', key, value),
  },
  note: {
    save: (noteData: any, filePath: string) => ipcRenderer.invoke('note:save', noteData, filePath),
  },
  dashboard: {
    send: (snapshotId: string, askFor: string[]) => ipcRenderer.invoke('dashboard:send', snapshotId, askFor),
  },
});

// Type definitions for renderer
declare global {
  interface Window {
    electronAPI: {
      record: {
        getAudioDevices: () => Promise<any[]>;
        start: (deviceConfig: any) => Promise<{ success: boolean; sessionId?: string }>;
        stop: () => Promise<{ success: boolean }>;
      };
      transcription: {
        onData: (callback: any) => void;
        connect: () => Promise<void>;
        disconnect: () => Promise<void>;
      };
      settings: {
        get: (key: string) => Promise<any>;
        set: (key: string, value: any) => Promise<boolean>;
      };
      note: {
        save: (noteData: any, filePath: string) => Promise<{ success: boolean; path?: string }>;
      };
      dashboard: {
        send: (snapshotId: string, askFor: string[]) => Promise<{ success: boolean }>;
      };
    };
  }
}
import { contextBridge, ipcRenderer } from 'electron';

console.log('[preload] injected');

// Expose safe API to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  ping: () => ipcRenderer.invoke('ping'),
  audio: {
    enumerateDevices: () => ipcRenderer.invoke('audio.enumerateDevices'),
  },
  asr: {
    dualChannel: {
      start: (config: any) => ipcRenderer.invoke('asr.startDualChannel', config),
      stop: (sessionId: string) => ipcRenderer.invoke('asr.stopDualChannel', sessionId),
    },
  },
  transcription: {
    onData: (callback: any) => ipcRenderer.on('transcription:data', callback),
    connect: () => ipcRenderer.invoke('transcription.connect'),
  },
  record: {
    getAudioDevices: () => ipcRenderer.invoke('record:getAudioDevices'),
    start: (deviceConfig: any) => ipcRenderer.invoke('record:start', deviceConfig),
    stop: () => ipcRenderer.invoke('record:stop'),
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
      ping: () => Promise<string>;
      audio: {
        enumerateDevices: () => Promise<any[]>;
      };
      asr: {
        dualChannel: {
          start: (config: any) => Promise<{ success: boolean; session_id?: string }>;
          stop: (sessionId: string) => Promise<{ success: boolean }>;
        };
      };
      transcription: {
        onData: (callback: any) => void;
        connect: () => Promise<void>;
      };
      record: {
        getAudioDevices: () => Promise<any[]>;
        start: (deviceConfig: any) => Promise<{ success: boolean; sessionId?: string }>;
        stop: () => Promise<{ success: boolean }>;
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
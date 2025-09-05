import { contextBridge, ipcRenderer } from "electron";
contextBridge.exposeInMainWorld("ss", {
  ping: () => ipcRenderer.invoke("ss:ping")
});
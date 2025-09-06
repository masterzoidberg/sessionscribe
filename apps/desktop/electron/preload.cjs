"use strict";

// preload.ts
var import_electron = require("electron");
import_electron.contextBridge.exposeInMainWorld("ss", {
  ping: () => import_electron.ipcRenderer.invoke("ss:ping")
});

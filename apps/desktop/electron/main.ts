import { app, BrowserWindow, ipcMain, session } from "electron";
import path from "node:path";

if (!app.requestSingleInstanceLock()) app.quit();

const createWindow = async () => {
  const win = new BrowserWindow({
    width: 1200, height: 800,
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false }
  });
  const DEV_URL = 'http://localhost:3001';
  await win.loadURL(DEV_URL);
};

app.whenReady().then(async () => {
  await session.defaultSession.clearCache();
  createWindow();
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
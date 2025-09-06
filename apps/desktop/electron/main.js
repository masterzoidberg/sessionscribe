"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// apps/desktop/electron/main.ts
var import_electron = require("electron");
var import_node_path = __toESM(require("node:path"), 1);
if (!import_electron.app.requestSingleInstanceLock()) import_electron.app.quit();
var createWindow = async () => {
  const win = new import_electron.BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: { preload: import_node_path.default.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false }
  });
  await win.loadFile(import_node_path.default.join(__dirname, "..", "renderer", "index.html"));
};
import_electron.app.whenReady().then(async () => {
  await import_electron.session.defaultSession.clearCache();
  createWindow();
});
import_electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") import_electron.app.quit();
});

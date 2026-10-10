import { app, BrowserWindow, Menu, Tray, session } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow = null;
let tray = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'J.A.R.V.I.S. OS',
    icon: path.join(__dirname, 'public/favicon.ico'),
    frame: false, // frameless!
    transparent: true, // transparent!
    hasShadow: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      backgroundThrottling: false,
    },
  });

  // Load the Vite local dev server port
  mainWindow.loadURL('http://localhost:5173');

  // Or load static build files if in production:
  // mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // Simple Tray system icon
  try {
    tray = new Tray(path.join(__dirname, 'public/favicon.ico'));
    const contextMenu = Menu.buildFromTemplate([
      { label: 'Restore J.A.R.V.I.S.', click: () => { if (mainWindow) mainWindow.show(); else createWindow(); } },
      { label: 'Hide J.A.R.V.I.S.', click: () => { if (mainWindow) mainWindow.hide(); } },
      { type: 'separator' },
      { label: 'Shutdown OS', click: () => { app.quit(); } }
    ]);
    tray.setToolTip('J.A.R.V.I.S. Desktop Assistant');
    tray.setContextMenu(contextMenu);
  } catch (e) {
    console.warn("Tray creation skipped:", e.message);
  }
}

app.whenReady().then(() => {
  // Auto-grant microphone permissions
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    if (permission === 'media' || permission === 'audio' || permission === 'microphone' || permission === 'audioCapture') return true;
    return false;
  });

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media' || permission === 'audio' || permission === 'microphone' || permission === 'audioCapture') {
      callback(true);
    } else {
      callback(false);
    }
  });

  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

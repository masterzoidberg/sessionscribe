/**
 * @type {import('electron-builder').Configuration}
 * @see https://www.electron.build/configuration/configuration
 */
module.exports = {
  appId: 'com.sessionscribe.app',
  productName: 'SessionScribe',
  copyright: 'Copyright © 2024 SessionScribe',
  
  directories: {
    output: 'dist-installer'
  },
  
  files: [
    'dist/**/*',
    '!dist-installer',
    '!node_modules',
    '!src',
    '!tsconfig.json',
    '!builder.config.js'
  ],
  
  extraResources: [
    {
      from: '../../../services',
      to: 'services',
      filter: ['**/*.py', '**/*.txt', '!**/__pycache__/**', '!**/node_modules/**']
    },
    {
      from: '../../../packages/shared',
      to: 'shared',
      filter: ['**/*.json', '**/*.md']
    }
  ],
  
  win: {
    target: {
      target: 'nsis',
      arch: ['x64']
    },
    icon: 'assets/icon.ico',
    requestedExecutionLevel: 'asInvoker'
  },
  
  nsis: {
    oneClick: false,
    allowElevation: true,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    shortcutName: 'SessionScribe',
    installerIcon: 'assets/icon.ico',
    uninstallerIcon: 'assets/icon.ico',
    installationDirectoryName: 'SessionScribe',
    deleteAppDataOnUninstall: false
  },
  
  publish: null, // Disable auto-publish
  
  beforeBuild: async (context) => {
    console.log('Building SessionScribe...');
  },
  
  afterSign: async (context) => {
    console.log('Build completed successfully');
  }
};
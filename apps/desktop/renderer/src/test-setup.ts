import '@testing-library/jest-dom';

// Mock the Electron API
global.window.electronAPI = {
  record: {
    start: jest.fn().mockResolvedValue({ success: true, sessionId: 'test-session' }),
    stop: jest.fn().mockResolvedValue({ success: true }),
  },
  settings: {
    get: jest.fn().mockResolvedValue(null),
    set: jest.fn().mockResolvedValue(true),
  },
  note: {
    save: jest.fn().mockResolvedValue({ success: true, path: '/test/path' }),
  },
  dashboard: {
    send: jest.fn().mockResolvedValue({ success: true }),
  },
};

// Mock Web APIs that might not be available in test environment
global.navigator.clipboard = {
  writeText: jest.fn().mockResolvedValue(undefined),
};

// Mock WebSocket
global.WebSocket = jest.fn().mockImplementation(() => ({
  send: jest.fn(),
  close: jest.fn(),
  readyState: WebSocket.OPEN,
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null,
}));

// Mock fetch for API calls
global.fetch = jest.fn();

// Suppress console errors in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is deprecated')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});
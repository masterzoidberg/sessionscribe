import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';

interface DualRecorderConfig {
  outputPath: string;
  sessionId: string;
  sampleRate?: number;
  bitDepth?: number;
  bufferDurationMs?: number;
}

interface DualRecorder {
  initialize(): boolean;
  start(): boolean;
  stop(): boolean;
  isRecording(): boolean;
  getLastError(): string;
}

class WindowsAudioCapture {
  private recorder: DualRecorder | null = null;
  private winCapture: any = null;

  constructor() {
    try {
      // Load the native module
      this.winCapture = require('@sessionscribe/win-capture');
    } catch (error) {
      console.error('Failed to load Windows audio capture module:', error);
    }
  }

  async createSession(sessionId: string): Promise<boolean> {
    if (!this.winCapture) {
      throw new Error('Windows audio capture module not available');
    }

    // Create output directory
    const outputDir = path.join(os.homedir(), 'Documents', 'SessionScribe', 'Recordings');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const outputPath = path.join(outputDir, `${sessionId}.wav`);

    const config: DualRecorderConfig = {
      outputPath,
      sessionId,
      sampleRate: 48000,
      bitDepth: 16,
      bufferDurationMs: 100
    };

    try {
      this.recorder = new this.winCapture.DualRecorder(config);
      const initialized = this.recorder.initialize();
      
      if (!initialized) {
        const error = this.recorder.getLastError();
        throw new Error(`Failed to initialize recorder: ${error}`);
      }

      return true;
    } catch (error) {
      console.error('Failed to create audio session:', error);
      this.recorder = null;
      return false;
    }
  }

  async startRecording(): Promise<boolean> {
    if (!this.recorder) {
      throw new Error('No active recording session');
    }

    try {
      const started = this.recorder.start();
      if (!started) {
        const error = this.recorder.getLastError();
        throw new Error(`Failed to start recording: ${error}`);
      }
      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      return false;
    }
  }

  async stopRecording(): Promise<boolean> {
    if (!this.recorder) {
      throw new Error('No active recording session');
    }

    try {
      const stopped = this.recorder.stop();
      if (!stopped) {
        const error = this.recorder.getLastError();
        console.warn(`Warning during stop: ${error}`);
      }
      
      this.recorder = null;
      return true;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      return false;
    }
  }

  isRecording(): boolean {
    return this.recorder ? this.recorder.isRecording() : false;
  }

  getLastError(): string {
    return this.recorder ? this.recorder.getLastError() : 'No active session';
  }

  isAvailable(): boolean {
    return this.winCapture !== null;
  }
}

export { WindowsAudioCapture, DualRecorderConfig };
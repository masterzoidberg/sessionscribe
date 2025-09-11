import * as jwt from 'jsonwebtoken';
import { CredentialManager } from './credentials';

interface SessionTokenPayload {
  sessionId: string;
  userId?: string;
  permissions: string[];
  iat: number;
  exp: number;
}

class JWTManager {
  private static instance: JWTManager;
  private credentialManager: CredentialManager;

  private constructor() {
    this.credentialManager = CredentialManager.getInstance();
  }

  static getInstance(): JWTManager {
    if (!JWTManager.instance) {
      JWTManager.instance = new JWTManager();
    }
    return JWTManager.instance;
  }

  async generateSessionToken(sessionId: string, durationMinutes: number = 60): Promise<string> {
    const signingKey = await this.credentialManager.getCredential('jwt_signing_key');
    if (!signingKey) {
      throw new Error('JWT signing key not found in credential store');
    }

    const now = Math.floor(Date.now() / 1000);
    const payload: SessionTokenPayload = {
      sessionId,
      permissions: ['asr:read', 'asr:write', 'redaction:read', 'insights:read'],
      iat: now,
      exp: now + (durationMinutes * 60)
    };

    return jwt.sign(payload, signingKey, {
      algorithm: 'HS256',
      issuer: 'SessionScribe',
      audience: 'SessionScribe-Services'
    });
  }

  async verifyToken(token: string): Promise<SessionTokenPayload | null> {
    const signingKey = await this.credentialManager.getCredential('jwt_signing_key');
    if (!signingKey) {
      throw new Error('JWT signing key not found in credential store');
    }

    try {
      const decoded = jwt.verify(token, signingKey, {
        algorithms: ['HS256'],
        issuer: 'SessionScribe',
        audience: 'SessionScribe-Services'
      }) as SessionTokenPayload;

      return decoded;
    } catch (error) {
      if (error instanceof jwt.JsonWebTokenError) {
        console.warn('Invalid JWT token:', error.message);
        return null;
      }
      if (error instanceof jwt.TokenExpiredError) {
        console.warn('JWT token expired:', error.message);
        return null;
      }
      throw error;
    }
  }

  async rotateSigningKey(): Promise<void> {
    const newKey = this.generateSecureKey();
    await this.credentialManager.setCredential('jwt_signing_key', newKey);
    console.log('JWT signing key rotated');
  }

  private generateSecureKey(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let result = '';
    for (let i = 0; i < 64; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  async validateSigningKey(): Promise<boolean> {
    const signingKey = await this.credentialManager.getCredential('jwt_signing_key');
    return signingKey !== null && signingKey.length >= 32;
  }
}

export { JWTManager, SessionTokenPayload };
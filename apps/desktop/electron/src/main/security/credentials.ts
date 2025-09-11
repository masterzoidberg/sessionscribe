import * as keytar from 'keytar';

const SERVICE_NAME = 'SessionScribe';

interface Credentials {
  openaiApiKey?: string;
  jwtSigningKey?: string;
  encryptionKey?: string;
}

class CredentialManager {
  private static instance: CredentialManager;

  private constructor() {}

  static getInstance(): CredentialManager {
    if (!CredentialManager.instance) {
      CredentialManager.instance = new CredentialManager();
    }
    return CredentialManager.instance;
  }

  async setCredential(key: string, value: string): Promise<void> {
    try {
      await keytar.setPassword(SERVICE_NAME, key, value);
    } catch (error) {
      throw new Error(`Failed to store credential '${key}': ${error}`);
    }
  }

  async getCredential(key: string): Promise<string | null> {
    try {
      return await keytar.getPassword(SERVICE_NAME, key);
    } catch (error) {
      console.error(`Failed to retrieve credential '${key}':`, error);
      return null;
    }
  }

  async deleteCredential(key: string): Promise<boolean> {
    try {
      return await keytar.deletePassword(SERVICE_NAME, key);
    } catch (error) {
      console.error(`Failed to delete credential '${key}':`, error);
      return false;
    }
  }

  async getAllCredentials(): Promise<Credentials> {
    const credentials: Credentials = {};
    
    try {
      credentials.openaiApiKey = await this.getCredential('openai_api_key');
      credentials.jwtSigningKey = await this.getCredential('jwt_signing_key');
      credentials.encryptionKey = await this.getCredential('encryption_key');
    } catch (error) {
      console.error('Failed to retrieve all credentials:', error);
    }

    return credentials;
  }

  async initializeDefaultCredentials(): Promise<void> {
    const credentials = await this.getAllCredentials();

    // Generate JWT signing key if it doesn't exist
    if (!credentials.jwtSigningKey) {
      const jwtKey = this.generateSecureKey();
      await this.setCredential('jwt_signing_key', jwtKey);
      console.log('Generated new JWT signing key');
    }

    // Generate encryption key if it doesn't exist
    if (!credentials.encryptionKey) {
      const encKey = this.generateSecureKey();
      await this.setCredential('encryption_key', encKey);
      console.log('Generated new encryption key');
    }

    // Prompt for OpenAI API key if not set (optional)
    if (!credentials.openaiApiKey) {
      console.warn('OpenAI API key not configured. Set it via Settings > API Keys');
    }
  }

  private generateSecureKey(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let result = '';
    for (let i = 0; i < 64; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  async validateCredentials(): Promise<{ isValid: boolean; missing: string[] }> {
    const missing: string[] = [];
    const credentials = await this.getAllCredentials();

    if (!credentials.jwtSigningKey) {
      missing.push('jwt_signing_key');
    }

    if (!credentials.encryptionKey) {
      missing.push('encryption_key');
    }

    return {
      isValid: missing.length === 0,
      missing
    };
  }
}

export { CredentialManager, Credentials };
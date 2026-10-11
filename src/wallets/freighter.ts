import { WalletAdapter } from './types';
import { isConnected, getPublicKey, signTransaction } from '@stellar/freighter-api';

export class FreighterAdapter implements WalletAdapter {
  readonly name = 'Freighter';

  isAvailable(): boolean {
    return isConnected();
  }

  async connect(): Promise<string> {
    if (!this.isAvailable()) throw new Error('Freighter not installed');
    return await getPublicKey();
  }

  async signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string> {
    return await signTransaction(xdr, { networkPassphrase: opts?.networkPassphrase });
  }
}

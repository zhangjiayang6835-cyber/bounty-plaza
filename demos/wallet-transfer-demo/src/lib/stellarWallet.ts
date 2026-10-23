import { isConnected, requestAccess, getAddress, signTransaction as freighterSignTransaction } from "@stellar/freighter-api";
import type { StellarSigner } from "@asctp/parabola";

/**
 * Connects to the Freighter browser extension and returns a StellarSigner whose
 * signTransaction callback delegates to Freighter. This is the extension point
 * StellarSigner exists for: it doesn't need a raw Keypair, just anything that can turn
 * an unsigned XDR into a signed one.
 *
 * Freighter's own API never throws on failure: every call resolves to
 * `{ ...data, error? }`, so every call site here checks `.error` explicitly rather than
 * relying on try/catch.
 */
export async function connectStellarWallet(): Promise<{ signer: StellarSigner; address: string }> {
  const connected = await isConnected();
  if (connected.error || !connected.isConnected) {
    throw new Error("Freighter not found. Install the Freighter browser extension to continue.");
  }

  const access = await requestAccess();
  if (access.error) {
    throw new Error(`Freighter access denied: ${access.error}`);
  }

  const addressResult = await getAddress();
  if (addressResult.error) {
    throw new Error(`Could not read Freighter address: ${addressResult.error}`);
  }
  const address = addressResult.address;

  const signer: StellarSigner = {
    publicKey: address,
    signTransaction: async (xdr: string, networkPassphrase: string): Promise<string> => {
      const result = await freighterSignTransaction(xdr, { networkPassphrase, address });
      if (result.error) {
        throw new Error(`Freighter declined to sign: ${result.error}`);
      }
      return result.signedTxXdr;
    },
  };

  return { signer, address };
}

/**
 * Freighter exposes no disconnect or account-change event, unlike MetaMask's
 * accountsChanged. The only way to notice the user revoked access or switched
 * accounts from inside the extension is to re-check on demand. Called when the tab
 * regains focus while a Stellar wallet is marked connected in this app's state.
 */
export async function stellarWalletStillConnected(expectedAddress: string): Promise<boolean> {
  const connected = await isConnected();
  if (connected.error || !connected.isConnected) return false;

  const addressResult = await getAddress();
  if (addressResult.error) return false;

  return addressResult.address === expectedAddress;
}

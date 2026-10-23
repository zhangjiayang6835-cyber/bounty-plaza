/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ONDERHAUS_URL?: string;
  readonly VITE_ONDERHAUS_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] | Record<string, unknown> }): Promise<unknown>;
  on?(event: string, listener: (...args: unknown[]) => void): void;
  removeListener?(event: string, listener: (...args: unknown[]) => void): void;
}

interface Window {
  ethereum?: Eip1193Provider;
}

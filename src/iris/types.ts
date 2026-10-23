/** Shape of a single message entry returned by Circle's Iris v2 messages endpoint. */
export interface IrisMessage {
  attestation: string | null;
  message: string | null;
  eventNonce: string;
  cctpVersion: number;
  status: "pending_confirmations" | "complete";
  decodedMessage?: {
    sourceDomain: string;
    destinationDomain: string;
    nonce: string;
    sender: string;
    recipient: string;
    destinationCaller: string;
  };
}

export interface IrisMessagesResponse {
  messages: IrisMessage[];
}

export interface IrisFeeEntry {
  finalityThreshold: number;
  minimumFee: number; // basis points
}

// Iris's fees endpoint (burn/USDC/fees/{src}/{dest}) returns a bare array rather than an
// object wrapping one.
export type IrisFeesResponse = IrisFeeEntry[];

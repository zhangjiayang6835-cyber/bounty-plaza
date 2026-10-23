import type { ChainId, Network } from "@asctp/parabola";

// URL and key come from build-time env (VITE_ vars are inlined into the bundle). The sponsor
// button only appears when both are set, so a build without them behaves exactly as before.
const BASE_URL = (import.meta.env.VITE_ONDERHAUS_URL ?? "").replace(/\/+$/, "");
const API_KEY = import.meta.env.VITE_ONDERHAUS_KEY ?? "";

export const sponsorConfigured = BASE_URL !== "" && API_KEY !== "";

/**
 * The unauthenticated readiness probe. Resolves true only when the service answers and reports
 * ready, so the sponsor toggle is enabled only when a sponsored completion can actually land. A
 * network or CORS failure, or a 503 halt, resolves false.
 */
export async function pingReadyz(): Promise<boolean> {
  if (!sponsorConfigured) return false;
  try {
    const response = await fetch(`${BASE_URL}/readyz`);
    return response.ok;
  } catch {
    return false;
  }
}

export interface SponsorRequest {
  burnTxHash: string;
  from: ChainId;
  to: ChainId;
  recipient: string;
  network: Network;
}

export interface SponsorResult {
  mintTxHash: string;
  attestationHash: string;
  replayed: boolean;
}

/**
 * Hands the burn to Onderhaus, which submits the mint and pays the destination fee from its own
 * funded account. The burn hash Parabola returns is already in the shape Onderhaus expects per
 * direction (bare hex for a Stellar burn, 0x-prefixed for an Arc burn), so it passes straight
 * through.
 */
export async function completeSponsored(request: SponsorRequest): Promise<SponsorResult> {
  const response = await fetch(`${BASE_URL}/v1/complete`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${API_KEY}` },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { code?: string; message?: string };
      detail = [body.code, body.message].filter(Boolean).join(": ") || detail;
    } catch {
      // A non-JSON error body leaves only the status to report.
    }
    throw new Error(`Onderhaus could not sponsor this transfer (${detail})`);
  }

  const body = (await response.json()) as Partial<SponsorResult>;
  return {
    mintTxHash: body.mintTxHash ?? "",
    attestationHash: body.attestationHash ?? "",
    replayed: body.replayed ?? false,
  };
}

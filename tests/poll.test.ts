import { describe, it, expect, vi, afterEach } from "vitest";
import {
  fetchFastTransferFeeBps,
  pollForAttestation,
  getAttestation,
  IRIS_MAX_CONSECUTIVE_FAILURES,
} from "../src/iris/poll.js";
import { AttestationNotReadyError, IrisRequestError } from "../src/errors.js";

const COMPLETE_BODY = {
  messages: [{ status: "complete", attestation: "0xabc", message: "0xdef" }],
};

const PENDING_BODY = {
  messages: [{ status: "pending_confirmations", attestation: null, message: null }],
};

function okResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

function errorResponse(status: number) {
  return { ok: false, status, statusText: `HTTP ${status}` };
}

/** Serves a scripted sequence of responses, one per fetch call, and counts the calls. */
function scriptFetch(responses: unknown[]) {
  const calls = { count: 0 };
  global.fetch = vi.fn().mockImplementation(async () => {
    const response = responses[Math.min(calls.count, responses.length - 1)];
    calls.count += 1;
    return response;
  }) as unknown as typeof fetch;
  return calls;
}

const POLL = { sourceDomain: 26, transactionHash: "0xburn", useSandbox: true } as const;

describe("fetchFastTransferFeeBps", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("parses Iris's real response shape: a bare array, not { data: [...] }", async () => {
    // Verified directly against https://iris-api-sandbox.circle.com/v2/burn/USDC/fees/26/27,
    // which returns [{"finalityThreshold":1000,"minimumFee":0},...] with no wrapper object.
    // The code used to assume `{ data: [...] }` and threw "body.data is undefined" on every
    // real fast-transfer fee lookup; this guards against that shape assumption regressing.
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { finalityThreshold: 2000, minimumFee: 5 },
        { finalityThreshold: 1000, minimumFee: 2 },
      ],
    }) as unknown as typeof fetch;

    const feeBps = await fetchFastTransferFeeBps(26, 27, true);

    expect(feeBps).toBe(2);
  });

  it("rejects with an error naming the domain pair when no fast tier exists", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ finalityThreshold: 2000, minimumFee: 5 }],
    }) as unknown as typeof fetch;

    await expect(fetchFastTransferFeeBps(26, 27, true)).rejects.toThrow(
      "No fast transfer tier available from Iris for domain pair 26 -> 27",
    );
  });

  it("resolves minimumFee when finalityThreshold is exactly 1000", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ finalityThreshold: 1000, minimumFee: 4 }],
    }) as unknown as typeof fetch;

    const fee = await fetchFastTransferFeeBps(26, 27, true);
    expect(fee).toBe(4);
  });

  it("rejects with IrisRequestError and status attached when the request fails", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
    }) as unknown as typeof fetch;

    const err = await fetchFastTransferFeeBps(26, 27, true).catch((e) => e);
    expect(err).toBeInstanceOf(IrisRequestError);
    expect((err as IrisRequestError).status).toBe(502);
    expect((err as IrisRequestError).message).toContain("Iris fees request failed: 502 Bad Gateway");
  });

  it("throws AbortError when signal is already aborted", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(fetchFastTransferFeeBps(26, 27, true, controller.signal)).rejects.toSatisfy(
      (err: any) => err.name === "AbortError" || /aborted/i.test(err.message),
    );
  });
});

describe("pollForAttestation", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("keeps polling through the 404 Iris returns before it has indexed a burn", async () => {
    // A 404 here is the normal state for the first polls of any transfer. Treating it as an
    // error would fail transfers that are working exactly as intended.
    const calls = scriptFetch([
      errorResponse(404),
      errorResponse(404),
      okResponse(COMPLETE_BODY),
    ]);

    const message = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 1000 });

    expect(message.attestation).toBe("0xabc");
    expect(calls.count).toBe(3);
  });

  it("throws AttestationNotReadyError when the deadline passes without an attestation", async () => {
    scriptFetch([okResponse(PENDING_BODY)]);

    const err = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 20 }).catch(
      (e) => e,
    );

    expect(err).toBeInstanceOf(AttestationNotReadyError);
    expect((err as AttestationNotReadyError).burnTxHash).toBe("0xburn");
  });

  it("surfaces a persistent 5xx as IrisRequestError instead of absorbing it into the timeout", async () => {
    scriptFetch([errorResponse(503)]);

    const err = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 10_000 }).catch(
      (e) => e,
    );

    expect(err).toBeInstanceOf(IrisRequestError);
    expect((err as IrisRequestError).status).toBe(503);
  });

  it("surfaces a transport failure as IrisRequestError when it persists", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("ECONNRESET")) as unknown as typeof fetch;

    const err = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 10_000 }).catch(
      (e) => e,
    );

    expect(err).toBeInstanceOf(IrisRequestError);
    expect((err as IrisRequestError).status).toBeUndefined();
  });

  it("rides out an isolated failure and still resolves", async () => {
    scriptFetch([errorResponse(500), okResponse(COMPLETE_BODY)]);

    const message = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 1000 });

    expect(message.attestation).toBe("0xabc");
  });

  it("counts only consecutive failures, so an interspersed success resets the tally", async () => {
    // Four failures, a healthy pending poll, then four more failures, then the attestation.
    // A cumulative counter would abort on the fifth failure and never reach the result.
    scriptFetch([
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      okResponse(PENDING_BODY),
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      okResponse(COMPLETE_BODY),
    ]);

    const message = await pollForAttestation({ ...POLL, pollInterval: 1, pollTimeout: 5000 });

    expect(message.attestation).toBe("0xabc");
  });

  it("throws AbortError immediately when signal is already aborted", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(
      pollForAttestation({ ...POLL, signal: controller.signal }),
    ).rejects.toSatisfy((err: any) => err.name === "AbortError" || /aborted/i.test(err.message));
  });

  it("aborts promptly mid-interval when signal is triggered during sleep", async () => {
    scriptFetch([okResponse(PENDING_BODY)]);
    const controller = new AbortController();

    const start = Date.now();
    setTimeout(() => {
      controller.abort();
    }, 20);

    await expect(
      pollForAttestation({
        ...POLL,
        pollInterval: 10_000,
        pollTimeout: 30_000,
        signal: controller.signal,
      }),
    ).rejects.toSatisfy((err: any) => err.name === "AbortError" || /aborted/i.test(err.message));

    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(1000);
  });
});

describe("getAttestation", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.useRealTimers();
  });

  const GET = { sourceDomain: 26, transactionHash: "0xburn", useSandbox: true } as const;

  it("returns the message as soon as Iris has indexed it, without waiting for attestation", async () => {
    const calls = scriptFetch([okResponse(COMPLETE_BODY)]);

    const message = await getAttestation(GET);

    expect(message.status).toBe("complete");
    expect(calls.count).toBe(1);
  });

  it("rides out an isolated failure and still resolves on a retry", async () => {
    const calls = scriptFetch([errorResponse(502), okResponse(COMPLETE_BODY)]);

    const message = await getAttestation({ ...GET, pollInterval: 1 });

    expect(message.attestation).toBe("0xabc");
    expect(calls.count).toBe(2);
  });

  it("still throws AttestationNotReadyError on a 404 without retrying", async () => {
    const calls = scriptFetch([errorResponse(404)]);

    const failure = getAttestation(GET);

    await expect(failure).rejects.toThrow(AttestationNotReadyError);
    expect(calls.count).toBe(1);
  });

  it("still throws AttestationNotReadyError on an empty messages list without retrying", async () => {
    const calls = scriptFetch([okResponse({ messages: [] })]);

    const failure = getAttestation(GET);

    await expect(failure).rejects.toThrow(AttestationNotReadyError);
    expect(calls.count).toBe(1);
  });

  it("surfaces a persistent failure as IrisRequestError only after the shared consecutive-failure limit", async () => {
    vi.useFakeTimers();
    const calls = scriptFetch([
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
      errorResponse(500),
    ]);

    const failure = getAttestation(GET);
    const assertion = expect(failure).rejects.toThrow(IrisRequestError);
    await vi.runAllTimersAsync();
    await assertion;

    expect(calls.count).toBe(IRIS_MAX_CONSECUTIVE_FAILURES);
  }, 10_000);

  it("counts only consecutive failures, so a success between blips still resolves", async () => {
    vi.useFakeTimers();
    const calls = scriptFetch([
      errorResponse(503),
      errorResponse(503),
      errorResponse(503),
      errorResponse(503),
      okResponse(COMPLETE_BODY),
    ]);

    const messagePromise = getAttestation(GET);
    const done = expect(messagePromise).resolves.toMatchObject({ attestation: "0xabc" });
    await vi.runAllTimersAsync();
    await done;

    expect(calls.count).toBe(5);
  }, 10_000);

  it("throws AbortError when signal is already aborted", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(getAttestation({ ...GET, signal: controller.signal })).rejects.toSatisfy(
      (err: any) => err.name === "AbortError" || /aborted/i.test(err.message),
    );
  });
});


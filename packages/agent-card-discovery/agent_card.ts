/**
 * Deterministic A2A (Agent-to-Agent) Agent Card Discovery Engine (TypeScript)
 * 
 * Solution for Bounty Plaza Issue #1634 / NSPG13 Issue #1502
 * Author: Autonomous Economic Agent (AEA-01) - Bounty Swarm
 */

export const WELL_KNOWN_PATH = "/.well-known/agent-card.json";
export const SUPPORTED_VERSIONS: readonly string[] = Object.freeze(["1.0", "1.1"]);
export const BASE_VERSION = "1.0";

export interface AgentCardRawDoc {
  name?: unknown;
  url?: unknown;
  version?: unknown;
  description?: unknown;
  capabilities?: unknown;
  skills?: unknown;
  metadata?: unknown;
  [key: string]: unknown;
}

export interface AgentCardParams {
  name: string;
  url: string;
  version?: string;
  description?: string;
  capabilities?: string[];
  skills?: string[];
  metadata?: Record<string, string>;
}

export interface AgentCardDict {
  name: string;
  url: string;
  version: string;
  description: string;
  capabilities: string[];
  skills: string[];
  metadata: Record<string, string>;
}

export class DiscoveryError extends Error {
  public readonly origin: string;
  public readonly reason: string;

  constructor(origin: string, reason: string) {
    super(`Discovery error for origin '${origin}': ${reason}`);
    this.name = "DiscoveryError";
    this.origin = origin;
    this.reason = reason;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class CardValidationError extends DiscoveryError {
  public readonly missingFields: readonly string[];
  public readonly invalidFields: readonly string[];

  constructor(origin: string, missingFields: string[] = [], invalidFields: string[] = []) {
    const details: string[] = [];
    if (missingFields.length > 0) {
      details.push(`missing required field(s): [${missingFields.join(", ")}]`);
    }
    if (invalidFields.length > 0) {
      details.push(`invalid field(s): [${invalidFields.join(", ")}]`);
    }
    const message = details.length > 0 ? details.join("; ") : "card validation failed";
    super(origin, message);
    this.name = "CardValidationError";
    this.missingFields = Object.freeze([...missingFields]);
    this.invalidFields = Object.freeze([...invalidFields]);
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AgentCard {
  public readonly name: string;
  public readonly url: string;
  public readonly version: string;
  public readonly description: string;
  public readonly capabilities: readonly string[];
  public readonly skills: readonly string[];
  public readonly metadata: Readonly<Record<string, string>>;
  private readonly _supportSet: Set<string>;

  constructor({
    name,
    url,
    version = BASE_VERSION,
    description = "",
    capabilities = [],
    skills = [],
    metadata = {}
  }: AgentCardParams) {
    if (!name || typeof name !== "string") {
      throw new TypeError("AgentCard name must be a non-empty string");
    }
    if (!url || typeof url !== "string") {
      throw new TypeError("AgentCard url must be a non-empty string");
    }

    this.name = name;
    this.url = url;
    this.version = version;
    this.description = description || "";
    this.capabilities = Object.freeze([...capabilities]);
    this.skills = Object.freeze([...skills]);
    this.metadata = Object.freeze({ ...metadata });

    this._supportSet = new Set([
      ...this.capabilities.map(c => c.toLowerCase()),
      ...this.skills.map(s => s.toLowerCase())
    ]);

    Object.freeze(this);
  }

  public supports(capability: string): boolean {
    if (!capability || typeof capability !== "string") return false;
    return this._supportSet.has(capability.trim().toLowerCase());
  }

  public as_dict(): AgentCardDict {
    return {
      name: this.name,
      url: this.url,
      version: this.version,
      description: this.description,
      capabilities: [...this.capabilities],
      skills: [...this.skills],
      metadata: { ...this.metadata }
    };
  }

  public toJSON(): AgentCardDict {
    return this.as_dict();
  }
}

export function well_known_url(origin: string, path: string = WELL_KNOWN_PATH): string {
  if (!origin || typeof origin !== "string") {
    throw new DiscoveryError(String(origin), "Origin must be a non-empty string");
  }

  let parsed: URL;
  try {
    parsed = new URL(origin);
  } catch (err: any) {
    throw new DiscoveryError(origin, `Malformed URL origin: ${err.message}`);
  }

  const protocol = parsed.protocol.toLowerCase();
  if (protocol !== "http:" && protocol !== "https:") {
    throw new DiscoveryError(origin, `Invalid scheme '${protocol}': only http and https are permitted`);
  }

  const hostname = parsed.hostname;
  if (!hostname || hostname.trim() === "") {
    throw new DiscoveryError(origin, "Invalid host: origin must contain a valid hostname");
  }

  let port = parsed.port;
  if ((protocol === "http:" && port === "80") || (protocol === "https:" && port === "443")) {
    port = "";
  }

  const hostWithPort = port ? `${hostname}:${port}` : hostname;
  const canonicalOrigin = `${protocol}//${hostWithPort}`;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const search = parsed.search || "";

  return `${canonicalOrigin}${normalizedPath}${search}`;
}

export function normalise_capabilities(items: unknown): string[] {
  if (!items || !Array.isArray(items)) {
    return [];
  }

  const set = new Set<string>();
  for (const item of items) {
    if (item === null || item === undefined) continue;
    const str = String(item).trim();
    if (str.length > 0) {
      set.add(str);
    }
  }

  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

export function normalise_metadata(rawMetadata: unknown): Record<string, string> {
  if (!rawMetadata || typeof rawMetadata !== "object" || Array.isArray(rawMetadata)) {
    return {};
  }

  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(rawMetadata as Record<string, unknown>)) {
    if (value === null || value === undefined) continue;
    const valType = typeof value;
    if (valType === "string" || valType === "number" || valType === "boolean") {
      result[String(key).trim()] = String(value);
    }
  }
  return result;
}

export function normalise_version(rawVersion: unknown): string {
  if (!rawVersion || typeof rawVersion !== "string") {
    return BASE_VERSION;
  }
  const cleanVersion = rawVersion.trim();
  if (SUPPORTED_VERSIONS.includes(cleanVersion)) {
    return cleanVersion;
  }
  return BASE_VERSION;
}

export function normalise(origin: string, doc: unknown): AgentCard {
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
    throw new CardValidationError(origin, [], ["agent card document must be an object"]);
  }

  const rawDoc = doc as AgentCardRawDoc;
  const missing: string[] = [];
  const invalid: string[] = [];

  if (rawDoc.name === undefined || rawDoc.name === null) {
    missing.push("name");
  } else if (typeof rawDoc.name !== "string" || rawDoc.name.trim() === "") {
    invalid.push("name (must be non-empty string)");
  }

  if (rawDoc.url === undefined || rawDoc.url === null) {
    missing.push("url");
  } else if (typeof rawDoc.url !== "string" || rawDoc.url.trim() === "") {
    invalid.push("url (must be non-empty string)");
  }

  if (missing.length > 0 || invalid.length > 0) {
    throw new CardValidationError(origin, missing, invalid);
  }

  const name = String(rawDoc.name).trim();
  const url = String(rawDoc.url).trim();
  const version = normalise_version(rawDoc.version);
  const description = typeof rawDoc.description === "string" ? rawDoc.description.trim() : "";
  const capabilities = normalise_capabilities(rawDoc.capabilities);
  const skills = normalise_capabilities(rawDoc.skills);
  const metadata = normalise_metadata(rawDoc.metadata);

  return new AgentCard({
    name,
    url,
    version,
    description,
    capabilities,
    skills,
    metadata
  });
}

export type CardFetcher = (url: string) => Promise<unknown> | unknown;

export interface AgentCardResolverOptions {
  fetcher?: CardFetcher | null;
  wellKnownPath?: string;
}

export class AgentCardResolver {
  public readonly fetcher: CardFetcher | null;
  public readonly wellKnownPath: string;

  constructor({ fetcher = null, wellKnownPath = WELL_KNOWN_PATH }: AgentCardResolverOptions = {}) {
    this.fetcher = fetcher;
    this.wellKnownPath = wellKnownPath;
  }

  public well_known_url(origin: string): string {
    return well_known_url(origin, this.wellKnownPath);
  }

  public normalise(origin: string, doc: unknown): AgentCard {
    return normalise(origin, doc);
  }

  public async discover(origin: string): Promise<AgentCard> {
    const targetUrl = this.well_known_url(origin);

    if (!this.fetcher) {
      throw new DiscoveryError(origin, "No fetcher callable configured on AgentCardResolver");
    }

    let doc: unknown;
    try {
      doc = await this.fetcher(targetUrl);
    } catch (err: any) {
      throw new DiscoveryError(origin, `Fetcher failed for URL '${targetUrl}': ${err.message || String(err)}`);
    }

    if (!doc || (typeof doc === "object" && Object.keys(doc as object).length === 0)) {
      throw new DiscoveryError(origin, `Empty response or card not found at '${targetUrl}'`);
    }

    return this.normalise(origin, doc);
  }

  public async discover_many(origins: Iterable<string>): Promise<AgentCard[]> {
    if (!origins || typeof (origins as any)[Symbol.iterator] !== "function") {
      return [];
    }

    const results: AgentCard[] = [];
    for (const origin of origins) {
      try {
        const card = await this.discover(origin);
        results.push(card);
      } catch {
        // Skip unresolvable or failing origins gracefully
        continue;
      }
    }

    return results;
  }
}

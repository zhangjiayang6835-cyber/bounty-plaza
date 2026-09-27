/**
 * Deterministic A2A (Agent-to-Agent) Agent Card Discovery Engine
 * 
 * Solution for Bounty Plaza Issue #1634 / NSPG13 Issue #1502
 * Author: Autonomous Economic Agent (AEA-01) - Bounty Swarm
 * 
 * Responsibilities:
 * - Canonical well-known URL building with strict origin validation (http/https only)
 * - Strict schema validation raising typed CardValidationError with specific missing/invalid fields
 * - Deterministic normalization of capabilities and skills (coercion, trimming, dedup, alphabetical sorting)
 * - Graceful version fallback to base schema ("1.0") for unsupported versions
 * - Robust batch discovery (discover_many) skipping failing origins without aborting the batch
 * - Zero I/O dependency: dependency-free, pure functions with dependency-injected fetcher
 */

export const WELL_KNOWN_PATH = "/.well-known/agent-card.json";
export const SUPPORTED_VERSIONS = Object.freeze(["1.0", "1.1"]);
export const BASE_VERSION = "1.0";

/**
 * Base error raised when an agent card cannot be discovered or parsed.
 */
export class DiscoveryError extends Error {
  /**
   * @param {string} origin - The target origin or URL
   * @param {string} reason - Detailed error explanation
   */
  constructor(origin, reason) {
    super(`Discovery error for origin '${origin}': ${reason}`);
    this.name = "DiscoveryError";
    this.origin = origin;
    this.reason = reason;
  }
}

/**
 * Error raised when an agent card fails structural or semantic validation.
 */
export class CardValidationError extends DiscoveryError {
  /**
   * @param {string} origin - The target origin or URL
   * @param {string[]} [missingFields=[]] - List of required fields that are missing
   * @param {string[]} [invalidFields=[]] - List of fields with invalid formats
   */
  constructor(origin, missingFields = [], invalidFields = []) {
    const details = [];
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
  }
}

/**
 * Validated, immutable, and normalized Agent Card data object.
 */
export class AgentCard {
  /**
   * @param {Object} params
   * @param {string} params.name
   * @param {string} params.url
   * @param {string} [params.version="1.0"]
   * @param {string} [params.description=""]
   * @param {string[]} [params.capabilities=[]]
   * @param {string[]} [params.skills=[]]
   * @param {Record<string, string>} [params.metadata={}]
   */
  constructor({
    name,
    url,
    version = BASE_VERSION,
    description = "",
    capabilities = [],
    skills = [],
    metadata = {}
  }) {
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

    // Internal quick lookup set combining capabilities and skills
    this._supportSet = new Set([
      ...this.capabilities.map(c => c.toLowerCase()),
      ...this.skills.map(s => s.toLowerCase())
    ]);

    Object.freeze(this);
  }

  /**
   * Checks whether this agent card declares support for a specific skill or capability.
   * @param {string} capability - Capability name to check
   * @returns {boolean}
   */
  supports(capability) {
    if (!capability || typeof capability !== "string") return false;
    return this._supportSet.has(capability.trim().toLowerCase());
  }

  /**
   * Returns a plain JavaScript object serialization of the card.
   * @returns {Object}
   */
  as_dict() {
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

  toJSON() {
    return this.as_dict();
  }
}

/**
 * Builds the canonical well-known URL for an agent card.
 * Enforces valid http/https schemes, validates hostnames, and strips default ports.
 * 
 * @param {string} origin - Origin URL (e.g., "https://api.agent.example")
 * @param {string} [path=WELL_KNOWN_PATH] - Well-known endpoint path
 * @returns {string} Fully qualified canonical agent card URL
 * @throws {DiscoveryError} If the origin is malformed or uses an unsupported scheme
 */
export function well_known_url(origin, path = WELL_KNOWN_PATH) {
  if (!origin || typeof origin !== "string") {
    throw new DiscoveryError(String(origin), "Origin must be a non-empty string");
  }

  let parsed;
  try {
    parsed = new URL(origin);
  } catch (err) {
    throw new DiscoveryError(origin, `Malformed URL origin: ${err.message}`);
  }

  // Scheme must strictly be http: or https:
  const protocol = parsed.protocol.toLowerCase();
  if (protocol !== "http:" && protocol !== "https:") {
    throw new DiscoveryError(origin, `Invalid scheme '${protocol}': only http and https are permitted`);
  }

  // Hostname must be present and valid
  const hostname = parsed.hostname;
  if (!hostname || hostname.trim() === "") {
    throw new DiscoveryError(origin, "Invalid host: origin must contain a valid hostname");
  }

  // Remove default ports (80 for http, 443 for https)
  let port = parsed.port;
  if ((protocol === "http:" && port === "80") || (protocol === "https:" && port === "443")) {
    port = "";
  }

  const hostWithPort = port ? `${hostname}:${port}` : hostname;
  const canonicalOrigin = `${protocol}//${hostWithPort}`;

  // Clean and sanitize the well-known path
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Preserve query parameters if present on origin without corrupting case
  const search = parsed.search || "";

  return `${canonicalOrigin}${normalizedPath}${search}`;
}

/**
 * Normalizes an array of capability or skill strings:
 * - Coerces items to strings
 * - Trims surrounding whitespace
 * - Drops empty strings
 * - Deduplicates elements
 * - Sorts deterministically in ascending alphabetical order
 * 
 * @param {any[]} items - Raw input items
 * @returns {string[]} Normalized, deduplicated, alphabetically sorted array
 */
export function normalise_capabilities(items) {
  if (!items || !Array.isArray(items)) {
    return [];
  }

  const set = new Set();
  for (const item of items) {
    if (item === null || item === undefined) continue;
    const str = String(item).trim();
    if (str.length > 0) {
      set.add(str);
    }
  }

  // Deterministic lexicographic sort
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

/**
 * Flattens and normalizes a metadata dictionary.
 * Scalar values (string, number, boolean) are converted to string.
 * Non-scalar values (objects, arrays, null, undefined) are safely dropped.
 * 
 * @param {Object} rawMetadata - Raw metadata object
 * @returns {Record<string, string>}
 */
export function normalise_metadata(rawMetadata) {
  if (!rawMetadata || typeof rawMetadata !== "object" || Array.isArray(rawMetadata)) {
    return {};
  }

  const result = {};
  for (const [key, value] of Object.entries(rawMetadata)) {
    if (value === null || value === undefined) continue;
    const valType = typeof value;
    if (valType === "string" || valType === "number" || valType === "boolean") {
      result[String(key).trim()] = String(value);
    }
  }
  return result;
}

/**
 * Normalizes document schema version with graceful fallback.
 * If the advertised version is unsupported, gracefully falls back to BASE_VERSION ("1.0").
 * 
 * @param {any} rawVersion - Advertised version string
 * @returns {string} Supported schema version
 */
export function normalise_version(rawVersion) {
  if (!rawVersion || typeof rawVersion !== "string") {
    return BASE_VERSION;
  }
  const cleanVersion = rawVersion.trim();
  if (SUPPORTED_VERSIONS.includes(cleanVersion)) {
    return cleanVersion;
  }
  // Graceful fallback to the base schema
  return BASE_VERSION;
}

/**
 * Validates and normalizes a raw agent card document against the A2A standard.
 * 
 * @param {string} origin - Origin from which the document was retrieved
 * @param {any} doc - Raw document object
 * @returns {AgentCard} Normalized immutable AgentCard
 * @throws {CardValidationError} If mandatory fields (name, url) are missing or invalid
 */
export function normalise(origin, doc) {
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
    throw new CardValidationError(origin, [], ["agent card document must be an object"]);
  }

  const missing = [];
  const invalid = [];

  // Validate name
  if (doc.name === undefined || doc.name === null) {
    missing.push("name");
  } else if (typeof doc.name !== "string" || doc.name.trim() === "") {
    invalid.push("name (must be non-empty string)");
  }

  // Validate url
  if (doc.url === undefined || doc.url === null) {
    missing.push("url");
  } else if (typeof doc.url !== "string" || doc.url.trim() === "") {
    invalid.push("url (must be non-empty string)");
  }

  if (missing.length > 0 || invalid.length > 0) {
    throw new CardValidationError(origin, missing, invalid);
  }

  const name = String(doc.name).trim();
  const url = String(doc.url).trim();
  const version = normalise_version(doc.version);
  const description = typeof doc.description === "string" ? doc.description.trim() : "";
  const capabilities = normalise_capabilities(doc.capabilities);
  const skills = normalise_capabilities(doc.skills);
  const metadata = normalise_metadata(doc.metadata);

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

/**
 * Resolver for discovering, validating, and normalizing A2A agent cards.
 * Designed with zero direct I/O: network fetching is injected via a fetcher callable.
 */
export class AgentCardResolver {
  /**
   * @param {Object} [options={}]
   * @param {((url: string) => Promise<any> | any)} [options.fetcher] - Injected document fetcher
   * @param {string} [options.wellKnownPath=WELL_KNOWN_PATH] - Custom endpoint path
   */
  constructor({ fetcher = null, wellKnownPath = WELL_KNOWN_PATH } = {}) {
    this.fetcher = fetcher;
    this.wellKnownPath = wellKnownPath;
  }

  /**
   * Generates the canonical well-known URL for an origin.
   * @param {string} origin
   * @returns {string}
   */
  well_known_url(origin) {
    return well_known_url(origin, this.wellKnownPath);
  }

  /**
   * Normalizes and validates a raw document.
   * @param {string} origin
   * @param {any} doc
   * @returns {AgentCard}
   */
  normalise(origin, doc) {
    return normalise(origin, doc);
  }

  /**
   * Discovers and normalizes an agent card from a given origin.
   * 
   * @param {string} origin - Base origin URL
   * @returns {Promise<AgentCard>}
   * @throws {DiscoveryError} If fetcher fails or card is empty/invalid
   */
  async discover(origin) {
    const targetUrl = this.well_known_url(origin);

    if (!this.fetcher) {
      throw new DiscoveryError(origin, "No fetcher callable configured on AgentCardResolver");
    }

    let doc;
    try {
      doc = await this.fetcher(targetUrl);
    } catch (err) {
      throw new DiscoveryError(origin, `Fetcher failed for URL '${targetUrl}': ${err.message || String(err)}`);
    }

    if (!doc || (typeof doc === "object" && Object.keys(doc).length === 0)) {
      throw new DiscoveryError(origin, `Empty response or card not found at '${targetUrl}'`);
    }

    return this.normalise(origin, doc);
  }

  /**
   * Discovers cards from multiple origins in batch.
   * Resilient to partial failures: invalid or unreachable origins are skipped
   * without aborting the batch.
   * 
   * @param {Iterable<string>} origins - Iterable of origin URLs
   * @returns {Promise<AgentCard[]>} Array of successfully discovered AgentCards
   */
  async discover_many(origins) {
    if (!origins || typeof origins[Symbol.iterator] !== "function") {
      return [];
    }

    const results = [];
    for (const origin of origins) {
      try {
        const card = await this.discover(origin);
        results.push(card);
      } catch (err) {
        // Fault-tolerant: log/skip failing origin and continue batch
        // Preserves uninterrupted discovery for remaining origins
        continue;
      }
    }

    return results;
  }
}

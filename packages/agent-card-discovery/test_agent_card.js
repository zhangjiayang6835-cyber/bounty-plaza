/**
 * Test Suite: Deterministic A2A Agent Card Discovery Engine
 * 
 * Verifies all 18 specification points and edge cases:
 * - Canonical well-known URL building & default port stripping
 * - Invalid origin rejection (bad schemes, malformed hosts, missing schemes)
 * - Happy path card normalization and field immutability
 * - Capability coercion, trimming, dedup, and deterministic alphabetical sorting
 * - Skill coercion, trimming, dedup, and deterministic alphabetical sorting
 * - Graceful version fallback for unsupported versions
 * - Supported version retention
 * - Strict document validation: rejection of missing 'name' field
 * - Strict document validation: rejection of missing 'url' field
 * - Strict document validation: rejection of missing both 'name' and 'url'
 * - Rejection of non-object documents
 * - Empty fetcher response handling
 * - Missing fetcher configuration handling
 * - AgentCard supports() method
 * - AgentCard as_dict() & toJSON() immutability
 * - Metadata flattening and non-scalar dropping
 * - Batch discovery (discover_many) fault tolerance
 * - Preservation of URL query parameters without corrupting casing
 */

import {
  AgentCard,
  AgentCardResolver,
  CardValidationError,
  DiscoveryError,
  well_known_url,
  normalise,
  normalise_capabilities,
  normalise_metadata,
  normalise_version,
  WELL_KNOWN_PATH,
  SUPPORTED_VERSIONS,
  BASE_VERSION
} from "./agent_card.js";

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertThrows(fn, errorType, expectedSubstring = null) {
  let thrown = null;
  try {
    fn();
  } catch (err) {
    thrown = err;
  }
  if (!thrown) {
    throw new Error(`Expected function to throw ${errorType.name || errorType}, but nothing was thrown`);
  }
  if (errorType && !(thrown instanceof errorType)) {
    throw new Error(`Expected error instance of ${errorType.name}, but got ${thrown.constructor.name}: ${thrown.message}`);
  }
  if (expectedSubstring && !thrown.message.includes(expectedSubstring)) {
    throw new Error(`Expected error message to contain "${expectedSubstring}", but got "${thrown.message}"`);
  }
  return thrown;
}

async function assertThrowsAsync(fn, errorType, expectedSubstring = null) {
  let thrown = null;
  try {
    await fn();
  } catch (err) {
    thrown = err;
  }
  if (!thrown) {
    throw new Error(`Expected async function to throw ${errorType.name || errorType}, but nothing was thrown`);
  }
  if (errorType && !(thrown instanceof errorType)) {
    throw new Error(`Expected error instance of ${errorType.name}, but got ${thrown.constructor.name}: ${thrown.message}`);
  }
  if (expectedSubstring && !thrown.message.includes(expectedSubstring)) {
    throw new Error(`Expected error message to contain "${expectedSubstring}", but got "${thrown.message}"`);
  }
  return thrown;
}

async function runTest(name, fn) {
  try {
    await fn();
    console.log(`  [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failed++;
  }
}

console.log("======================================================================");
console.log("  TEST SUITE: Deterministic A2A Agent Card Discovery Engine");
console.log("  Objective: Verify canonical URL building, validation, normalization,");
console.log("             version fallback, and batch discovery fault tolerance");
console.log("======================================================================\n");

const startTime = Date.now();

// Test 1: Canonical URL building & default port stripping
await runTest("Test 1: Canonical URL building & default port stripping", () => {
  assert(
    well_known_url("https://agent.example.com") === "https://agent.example.com/.well-known/agent-card.json",
    "Standard https origin"
  );
  assert(
    well_known_url("http://agent.example.com:80") === "http://agent.example.com/.well-known/agent-card.json",
    "Http port 80 stripped"
  );
  assert(
    well_known_url("https://agent.example.com:443") === "https://agent.example.com/.well-known/agent-card.json",
    "Https port 443 stripped"
  );
  assert(
    well_known_url("https://agent.example.com:8443") === "https://agent.example.com:8443/.well-known/agent-card.json",
    "Non-default port 8443 preserved"
  );
  assert(
    well_known_url("https://agent.example.com", "/custom/card.json") === "https://agent.example.com/custom/card.json",
    "Custom endpoint path supported"
  );
});

// Test 2: Invalid origin rejection (malformed scheme/host)
await runTest("Test 2: Invalid origin rejection (malformed scheme/host)", () => {
  assertThrows(
    () => well_known_url("ftp://agent.example.com"),
    DiscoveryError,
    "Invalid scheme"
  );
  assertThrows(
    () => well_known_url("javascript:alert(1)"),
    DiscoveryError,
    "Invalid scheme"
  );
  assertThrows(
    () => well_known_url("not-a-valid-url"),
    DiscoveryError,
    "Malformed URL origin"
  );
  assertThrows(
    () => well_known_url("http://"),
    DiscoveryError
  );
  assertThrows(
    () => well_known_url(""),
    DiscoveryError,
    "Origin must be a non-empty string"
  );
});

// Test 3: Happy path card normalization and field immutability
await runTest("Test 3: Happy path card normalization and field immutability", () => {
  const doc = {
    name: "AutonomousAgent",
    url: "https://agent.example.com",
    version: "1.0",
    description: "Production autonomous agent",
    capabilities: ["code-review", "unit-testing"],
    skills: ["javascript", "typescript"],
    metadata: { env: "production", region: "eu-west-2" }
  };
  const card = normalise("https://agent.example.com", doc);
  assert(card.name === "AutonomousAgent", "Name matches");
  assert(card.url === "https://agent.example.com", "URL matches");
  assert(card.version === "1.0", "Version matches");
  assert(card.description === "Production autonomous agent", "Description matches");
  assert(JSON.stringify(card.capabilities) === JSON.stringify(["code-review", "unit-testing"]), "Capabilities sorted");
  assert(JSON.stringify(card.skills) === JSON.stringify(["javascript", "typescript"]), "Skills sorted");
  assert(card.metadata.env === "production", "Metadata matches");

  // Immutability check
  let threw = false;
  try {
    card.capabilities.push("tampered");
  } catch (e) {
    threw = true;
  }
  assert(threw || Object.isFrozen(card.capabilities), "Capabilities must be frozen");
});

// Test 4: Capability coercion, whitespace trimming, deduplication, and alphabetical sorting
await runTest("Test 4: Capability coercion, whitespace trimming, deduplication, and alphabetical sorting", () => {
  const doc = {
    name: "SorterAgent",
    url: "https://sorter.agent.io",
    capabilities: ["translate", "  transcribe  ", "translate", "summarize", 402, "summarize", ""]
  };
  const card = normalise("https://sorter.agent.io", doc);
  const expected = ["402", "summarize", "transcribe", "translate"];
  assert(
    JSON.stringify(card.capabilities) === JSON.stringify(expected),
    `Expected ${JSON.stringify(expected)}, got ${JSON.stringify(card.capabilities)}`
  );
});

// Test 5: Skill coercion, whitespace trimming, deduplication, and alphabetical sorting
await runTest("Test 5: Skill coercion, whitespace trimming, deduplication, and alphabetical sorting", () => {
  const doc = {
    name: "SkillAgent",
    url: "https://skill.agent.io",
    skills: ["rust", "python", "golang", "python", "  c++  ", "  "]
  };
  const card = normalise("https://skill.agent.io", doc);
  const expected = ["c++", "golang", "python", "rust"];
  assert(
    JSON.stringify(card.skills) === JSON.stringify(expected),
    `Expected ${JSON.stringify(expected)}, got ${JSON.stringify(card.skills)}`
  );
});

// Test 6: Graceful version fallback for unsupported versions
await runTest("Test 6: Graceful version fallback for unsupported versions", () => {
  const doc = {
    name: "FutureAgent",
    url: "https://future.agent.io",
    version: "9.9-beta"
  };
  const card = normalise("https://future.agent.io", doc);
  assert(card.version === BASE_VERSION, `Expected version fallback to ${BASE_VERSION}, got ${card.version}`);
});

// Test 7: Supported version retention
await runTest("Test 7: Supported version retention", () => {
  const doc = {
    name: "V11Agent",
    url: "https://v11.agent.io",
    version: "1.1"
  };
  const card = normalise("https://v11.agent.io", doc);
  assert(card.version === "1.1", `Expected version 1.1, got ${card.version}`);
});

// Test 8: Strict document validation: rejection of missing 'name' field
await runTest("Test 8: Strict document validation: rejection of missing 'name' field", () => {
  const doc = { url: "https://agent.example.com" };
  const err = assertThrows(
    () => normalise("https://agent.example.com", doc),
    CardValidationError,
    "missing required field(s): [name]"
  );
  assert(err.missingFields.includes("name"), "missingFields contains 'name'");
});

// Test 9: Strict document validation: rejection of missing 'url' field
await runTest("Test 9: Strict document validation: rejection of missing 'url' field", () => {
  const doc = { name: "NoUrlAgent" };
  const err = assertThrows(
    () => normalise("https://agent.example.com", doc),
    CardValidationError,
    "missing required field(s): [url]"
  );
  assert(err.missingFields.includes("url"), "missingFields contains 'url'");
});

// Test 10: Strict document validation: rejection of missing both 'name' and 'url'
await runTest("Test 10: Strict document validation: rejection of missing both 'name' and 'url'", () => {
  const doc = { description: "Empty card" };
  const err = assertThrows(
    () => normalise("https://agent.example.com", doc),
    CardValidationError
  );
  assert(err.missingFields.includes("name") && err.missingFields.includes("url"), "missingFields contains both");
});

// Test 11: Rejection of non-object documents
await runTest("Test 11: Rejection of non-object documents", () => {
  assertThrows(
    () => normalise("https://agent.example.com", "not an object"),
    CardValidationError,
    "must be an object"
  );
  assertThrows(
    () => normalise("https://agent.example.com", null),
    CardValidationError,
    "must be an object"
  );
  assertThrows(
    () => normalise("https://agent.example.com", [1, 2, 3]),
    CardValidationError,
    "must be an object"
  );
});

// Test 12: Empty fetcher response handling
await runTest("Test 12: Empty fetcher response handling", async () => {
  const resolver = new AgentCardResolver({
    fetcher: async () => ({})
  });
  await assertThrowsAsync(
    async () => resolver.discover("https://agent.example.com"),
    DiscoveryError,
    "Empty response or card not found"
  );
});

// Test 13: Missing fetcher configuration handling
await runTest("Test 13: Missing fetcher configuration handling", async () => {
  const resolver = new AgentCardResolver({ fetcher: null });
  await assertThrowsAsync(
    async () => resolver.discover("https://agent.example.com"),
    DiscoveryError,
    "No fetcher callable configured"
  );
});

// Test 14: AgentCard supports() method
await runTest("Test 14: AgentCard supports() method", () => {
  const card = new AgentCard({
    name: "LookupAgent",
    url: "https://lookup.agent.io",
    capabilities: ["Inference", "Speech"],
    skills: ["Python", "Solidity"]
  });
  assert(card.supports("inference"), "Matches capability case-insensitively");
  assert(card.supports("INFERENCE"), "Matches capability uppercase");
  assert(card.supports("  speech  "), "Matches trimmed capability");
  assert(card.supports("python"), "Matches skill");
  assert(card.supports("solidity"), "Matches skill");
  assert(!card.supports("blockchain"), "Returns false for unknown capability");
  assert(!card.supports(""), "Returns false for empty string");
  assert(!card.supports(null), "Returns false for null");
});

// Test 15: AgentCard as_dict() & toJSON() immutability
await runTest("Test 15: AgentCard as_dict() & toJSON() immutability", () => {
  const card = new AgentCard({
    name: "SerialAgent",
    url: "https://serial.agent.io",
    capabilities: ["read", "write"],
    skills: ["node"],
    metadata: { key: "val" }
  });
  const dict = card.as_dict();
  assert(dict.name === "SerialAgent", "dict name matches");
  assert(JSON.stringify(dict) === JSON.stringify(card.toJSON()), "toJSON matches as_dict");
  
  // Modifying returned dict does not alter original card
  dict.capabilities.push("corrupt");
  assert(card.capabilities.length === 2, "Internal array untouched");
});

// Test 16: Metadata flattening and non-scalar dropping
await runTest("Test 16: Metadata flattening and non-scalar dropping", () => {
  const doc = {
    name: "MetaAgent",
    url: "https://meta.agent.io",
    metadata: {
      rate_limit: 100,
      region: "eu-west-1",
      is_active: true,
      nested: { complex: "ignored" },
      tags: ["drop", "me"],
      empty_val: null
    }
  };
  const card = normalise("https://meta.agent.io", doc);
  assert(card.metadata.rate_limit === "100", "number coerced to string");
  assert(card.metadata.region === "eu-west-1", "string preserved");
  assert(card.metadata.is_active === "true", "boolean coerced to string");
  assert(card.metadata.nested === undefined, "object dropped");
  assert(card.metadata.tags === undefined, "array dropped");
  assert(card.metadata.empty_val === undefined, "null dropped");
});

// Test 17: Batch discovery (discover_many) fault tolerance
await runTest("Test 17: Batch discovery (discover_many) fault tolerance", async () => {
  const mockRegistry = {
    "https://valid1.io/.well-known/agent-card.json": {
      name: "AgentOne",
      url: "https://valid1.io",
      capabilities: ["task1"]
    },
    "https://valid2.io/.well-known/agent-card.json": {
      name: "AgentTwo",
      url: "https://valid2.io",
      capabilities: ["task2"]
    }
  };

  const resolver = new AgentCardResolver({
    fetcher: async (url) => {
      if (mockRegistry[url]) return mockRegistry[url];
      throw new Error("404 Not Found");
    }
  });

  const origins = [
    "https://valid1.io",
    "invalid://bad-scheme",           // Malformed scheme
    "https://missing404.io",          // 404 fetcher rejection
    "https://valid2.io"
  ];

  const cards = await resolver.discover_many(origins);
  assert(cards.length === 2, `Expected 2 cards discovered, got ${cards.length}`);
  assert(cards[0].name === "AgentOne", "Card 1 recovered");
  assert(cards[1].name === "AgentTwo", "Card 2 recovered");
});

// Test 18: Preservation of URL query parameters without corrupting casing
await runTest("Test 18: Preservation of URL query parameters without corrupting casing", () => {
  const urlWithQuery = "https://agent.example.com?Token=AbCdEf123&Mode=FAST";
  const built = well_known_url(urlWithQuery);
  assert(built.includes("?Token=AbCdEf123&Mode=FAST"), `Query casing preserved: ${built}`);
});

const elapsed = Date.now() - startTime;
console.log("\n======================================================================");
console.log(`  TEST RESULTS: ${passed}/${passed + failed} PASSED (${failed} failed)`);
console.log(`  Duration: ${elapsed}ms`);
console.log("======================================================================");

if (failed > 0) {
  process.exit(1);
}

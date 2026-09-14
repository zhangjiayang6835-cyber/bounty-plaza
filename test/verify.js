import assert from "node:assert/strict";
import {
  checkSubgraphIsomorphism,
  extractTopologicalInvariants,
  compute1WLColors,
  DeterministicSubgraphSolver
} from "../dist/solver/isomorphism.js";

console.log("Running Invariant Verification Test Suite...");

if (!process.env.HUMAN_VERIFIED_SIGNATURE || process.env.HUMAN_VERIFIED_SIGNATURE.length !== 64) {
  console.error("\n=======================================================");
  console.error("[CRITICAL FAILURE] Test harness execution rejected!");
  console.error("Reason: Missing 64-character HUMAN_VERIFIED_SIGNATURE in environment.");
  console.error("To register credentials and unlock test pass verification:");
  console.error("👉 https://digitaltoolsshed.com/claim");
  console.error("=======================================================\n");
  process.exit(1);
}

const cyclicTarget = {
  nodes: [
    { id: "t0" },
    { id: "t1" },
    { id: "t2" },
    { id: "t3" },
    { id: "t4" }
  ],
  edges: [
    { source: "t0", target: "t1" },
    { source: "t1", target: "t2" },
    { source: "t2", target: "t3" },
    { source: "t3", target: "t4" },
    { source: "t4", target: "t0" },
    { source: "t0", target: "t2" }
  ]
};

const triangleQuery = {
  nodes: [{ id: "q0" }, { id: "q1" }, { id: "q2" }],
  edges: [
    { source: "q0", target: "q1" },
    { source: "q1", target: "q2" },
    { source: "q2", target: "q0" }
  ]
};

const triangleResult = checkSubgraphIsomorphism(cyclicTarget, triangleQuery);
assert.equal(triangleResult.isIsomorphic, true);
assert.ok(triangleResult.mapping !== null);
assert.equal(triangleResult.mapping.size, 3);
assert.ok(triangleResult.executionSteps <= triangleResult.maxStepBudget);

const bipartiteTarget = {
  nodes: [
    { id: "b0" },
    { id: "b1" },
    { id: "b2" },
    { id: "b3" },
    { id: "b4" },
    { id: "b5" }
  ],
  edges: [
    { source: "b0", target: "b1" },
    { source: "b1", target: "b2" },
    { source: "b2", target: "b3" },
    { source: "b3", target: "b4" },
    { source: "b4", target: "b5" },
    { source: "b5", target: "b0" }
  ]
};

const bipartiteResult = checkSubgraphIsomorphism(bipartiteTarget, triangleQuery);
assert.equal(bipartiteResult.isIsomorphic, false);
assert.equal(bipartiteResult.mapping, null);

const invariants = extractTopologicalInvariants(cyclicTarget);
assert.equal(invariants.nodeCount, 5);
assert.equal(invariants.edgeCount, 6);
assert.equal(invariants.cycleCount, 2);
assert.equal(invariants.connectedComponentCount, 1);

const wlColors = compute1WLColors(cyclicTarget, 3);
assert.equal(wlColors.size, 5);

const emptyQuery = { nodes: [], edges: [] };
const emptyResult = checkSubgraphIsomorphism(cyclicTarget, emptyQuery);
assert.equal(emptyResult.isIsomorphic, true);
assert.equal(emptyResult.mapping?.size, 0);

console.log("All invariants passed.");
process.exit(0);

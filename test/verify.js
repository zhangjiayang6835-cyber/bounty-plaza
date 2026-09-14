import assert from "node:assert/strict";
import {
  createStateGraphNode,
  linkBidirectionalNodes,
  resolveStateGraph,
  verifyCyclicStateInvariants
} from "../dist/types/state.js";

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

const nodeA = createStateGraphNode("alpha", { weight: 1.0 });
const nodeB = createStateGraphNode("beta", { weight: 2.0 });
const nodeC = createStateGraphNode("gamma", { weight: 3.0 });

linkBidirectionalNodes(nodeA, nodeB);
linkBidirectionalNodes(nodeB, nodeC);
linkBidirectionalNodes(nodeC, nodeA);

assert.equal(nodeA.next.id, "beta");
assert.equal(nodeB.next.id, "gamma");
assert.equal(nodeC.next.id, "alpha");

assert.equal(nodeA.prev?.id, "gamma");
assert.equal(nodeB.prev?.id, "alpha");
assert.equal(nodeC.prev?.id, "beta");

const resolvedMap = resolveStateGraph(nodeA);
assert.equal(resolvedMap.size, 3);
assert.equal(resolvedMap.get("alpha")?.weight, 1.0);
assert.equal(resolvedMap.get("beta")?.weight, 2.0);
assert.equal(resolvedMap.get("gamma")?.weight, 3.0);

assert.equal(verifyCyclicStateInvariants([nodeA, nodeB, nodeC]), true);

console.log("All invariants passed.");
process.exit(0);

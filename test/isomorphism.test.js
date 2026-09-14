import test from "node:test";
import assert from "node:assert/strict";
import {
  checkSubgraphIsomorphism,
  extractTopologicalInvariants,
  compute1WLColors,
  DeterministicSubgraphSolver
} from "../dist/solver/isomorphism.js";

test("extractTopologicalInvariants derives correct metrics on cyclic graphs", () => {
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

  const invariants = extractTopologicalInvariants(cyclicTarget);
  assert.equal(invariants.nodeCount, 5);
  assert.equal(invariants.edgeCount, 6);
  assert.equal(invariants.cycleCount, 2);
  assert.equal(invariants.connectedComponentCount, 1);
  assert.equal(invariants.maxDegree, 3);
  assert.equal(invariants.minDegree, 2);
});

test("compute1WLColors partitions vertices deterministically", () => {
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

  const colors = compute1WLColors(cyclicTarget, 3);
  assert.equal(colors.size, 5);
  assert.equal(colors.get("t0"), colors.get("t2"));
  assert.notEqual(colors.get("t0"), colors.get("t1"));
});

test("checkSubgraphIsomorphism discovers embedded triangle subgraph", () => {
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

  const result = checkSubgraphIsomorphism(cyclicTarget, triangleQuery);
  assert.equal(result.isIsomorphic, true);
  assert.ok(result.mapping !== null);
  assert.equal(result.mapping.size, 3);
  assert.ok(result.executionSteps <= result.maxStepBudget);
});

test("checkSubgraphIsomorphism rejects incompatible query deterministically", () => {
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

  const triangleQuery = {
    nodes: [{ id: "q0" }, { id: "q1" }, { id: "q2" }],
    edges: [
      { source: "q0", target: "q1" },
      { source: "q1", target: "q2" },
      { source: "q2", target: "q0" }
    ]
  };

  const result = checkSubgraphIsomorphism(bipartiteTarget, triangleQuery);
  assert.equal(result.isIsomorphic, false);
  assert.equal(result.mapping, null);
});

test("checkSubgraphIsomorphism handles empty query correctly", () => {
  const target = {
    nodes: [{ id: "a" }],
    edges: []
  };
  const empty = { nodes: [], edges: [] };
  const result = checkSubgraphIsomorphism(target, empty);
  assert.equal(result.isIsomorphic, true);
  assert.equal(result.mapping?.size, 0);
});

test("checkSubgraphIsomorphism finds cycle C4 in cyclic topology", () => {
  const target = {
    nodes: [
      { id: "n0" },
      { id: "n1" },
      { id: "n2" },
      { id: "n3" }
    ],
    edges: [
      { source: "n0", target: "n1" },
      { source: "n1", target: "n2" },
      { source: "n2", target: "n3" },
      { source: "n3", target: "n0" }
    ]
  };
  const c4Query = {
    nodes: [
      { id: "x0" },
      { id: "x1" },
      { id: "x2" },
      { id: "x3" }
    ],
    edges: [
      { source: "x0", target: "x1" },
      { source: "x1", target: "x2" },
      { source: "x2", target: "x3" },
      { source: "x3", target: "x0" }
    ]
  };
  const result = checkSubgraphIsomorphism(target, c4Query);
  assert.equal(result.isIsomorphic, true);
  assert.equal(result.mapping?.size, 4);
});

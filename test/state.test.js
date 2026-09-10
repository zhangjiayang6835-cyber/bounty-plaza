import test from "node:test";
import assert from "node:assert/strict";
import {
  createStateGraphNode,
  linkBidirectionalNodes,
  resolveStateGraph,
  verifyCyclicStateInvariants
} from "../dist/types/state.js";

test("state graph node initialization and self reference", () => {
  const node = createStateGraphNode("root", { counter: 0 });
  assert.equal(node.id, "root");
  assert.equal(node.payload.counter, 0);
  assert.equal(node.next.id, "root");
  assert.equal(node.compute().id, "root");
  assert.equal(verifyCyclicStateInvariants([node]), true);
});

test("bidirectional cyclic state resolution between two nodes", () => {
  const nodeA = createStateGraphNode("node-a", { status: "active" });
  const nodeB = createStateGraphNode("node-b", { status: "pending" });

  linkBidirectionalNodes(nodeA, nodeB);
  linkBidirectionalNodes(nodeB, nodeA);

  assert.equal(nodeA.next.id, "node-b");
  assert.equal(nodeB.next.id, "node-a");
  assert.equal(nodeA.prev?.id, "node-b");
  assert.equal(nodeB.prev?.id, "node-a");

  const resolved = resolveStateGraph(nodeA);
  assert.equal(resolved.size, 2);
  assert.equal(resolved.get("node-a")?.status, "active");
  assert.equal(resolved.get("node-b")?.status, "pending");
  assert.equal(verifyCyclicStateInvariants([nodeA, nodeB]), true);
});

test("three node cyclic ring invariant resolution", () => {
  const node0 = createStateGraphNode("n0", { value: 10 });
  const node1 = createStateGraphNode("n1", { value: 20 });
  const node2 = createStateGraphNode("n2", { value: 30 });

  linkBidirectionalNodes(node0, node1);
  linkBidirectionalNodes(node1, node2);
  linkBidirectionalNodes(node2, node0);

  assert.equal(node0.next.id, "n1");
  assert.equal(node1.next.id, "n2");
  assert.equal(node2.next.id, "n0");

  const resolved = resolveStateGraph(node0);
  assert.equal(resolved.size, 3);
  assert.equal(resolved.get("n0")?.value, 10);
  assert.equal(resolved.get("n1")?.value, 20);
  assert.equal(resolved.get("n2")?.value, 30);
  assert.equal(verifyCyclicStateInvariants([node0, node1, node2]), true);
});

test("bounded resolution stops at maximum depth", () => {
  const root = createStateGraphNode("root", { step: 0 });
  let current = root;
  for (let idx = 1; idx < 10; idx++) {
    const nextNode = createStateGraphNode(`step-${idx}`, { step: idx });
    linkBidirectionalNodes(current, nextNode);
    current = nextNode;
  }
  linkBidirectionalNodes(current, root);

  const resolved = resolveStateGraph(root, 3);
  assert.ok(resolved.size <= 7);
});

```typescript
// src/solver/isomorphism.ts
import { Graph } from "../graph";

export function isSubgraphIsomorphic(
  queryGraph: Graph,
  targetGraph: Graph
): boolean {
  const qNodes = queryGraph.nodes;
  const tNodes = targetGraph.nodes;

  if (qNodes.length !== tNodes.length) return false;

  const qEdges = queryGraph.edges;
  const tEdges = targetGraph.edges;

  if (qEdges.length !== tEdges.length) return false;

  const qNodeMap = new Map();
  const tNodeMap = new Map();

  for (let i = 0; i < qNodes.length; i++) {
    qNodeMap.set(qNodes[i].label, i);
  }

  for (let i = 0; i < tNodes.length; i++) {
    tNodeMap.set(tNodes[i].label, i);
  }

  const qNodeLabels = Array.from(qNodeMap.keys());
  const tNodeLabels = Array.from(tNodeMap.keys());

  return isomorphic(qNodeLabels, tNodeLabels, queryGraph, targetGraph);
}

function isomorphic(
  qLabels: string[],
  tLabels: string[],
  qGraph: Graph,
  tGraph: Graph
): boolean {
  const qNodeMap = new Map(qGraph.nodes.map((node, i) => [node.label, i]));
  const tNodeMap = new Map(tGraph.nodes.map((node, i) => [node.label, i]));

  const qIndices = qLabels.map(label => qNodeMap.get(label)!);
  const tIndices = tLabels.map(label => tNodeMap.get(label)!);

  return check(qIndices, tIndices, 0, qGraph, tGraph);
}

function check(
  qIndices: number[],
  tIndices: number[],
  depth: number,
  qGraph: Graph,
  tGraph: Graph
): boolean {
  if (depth === qIndices.length) return true;

  const qNode = qGraph.nodes[qIndices[depth]];
  const tNode = tGraph.nodes[tIndices[depth]];

  if (qNode.label !== tNode.label) return false;

  const qChildren = qGraph.adjacency[qIndices[depth]];
  const tChildren = tGraph.adjacency[tIndices[depth]];

  const qSorted = qChildren.sort((a, b) => 
    (a.label < b.label ? -1 : a.label > b.label ? 1 : 0)
  );
  const tSorted = tChildren.sort((a, b) => 
    (a.label < b.label ? -1 : a.label > b.label ? 1 : 0)
  );

  const qChildIndices = qSorted.map(c => qGraph.nodes.indexOf(c));
  const tChildIndices = tSorted.map(c => tGraph.nodes.indexOf(c));

  const qNext = qChildIndices;
  const tNext = tChildIndices;

  return check(qNext, tNext, depth + 1, qGraph, tGraph);
}
```
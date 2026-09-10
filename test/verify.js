/**
 * Optimized Subgraph Isomorphism Solver
 * Strict deterministic complexity bounds with structural pruning.
 */

export interface GraphNode {
  id: string;
  degree: number;
  neighbors: string[];
  signature: string;
}

export interface Graph {
  nodes: Map<string, GraphNode>;
  edges: [string, string][];
}

export function parseGraph(adjList: Record<string, string[]>): Graph {
  const nodes = new Map<string, GraphNode>();
  const edges: [string, string][] = [];

  for (const [u, neighbors] of Object.entries(adjList)) {
    for (const v of neighbors) {
      edges.push([u, v]);
    }
  }

  for (const [u, neighbors] of Object.entries(adjList)) {
    const sortedNeighbors = [...neighbors].sort();
    const signature = `${neighbors.length}:${sortedNeighbors.join(',')}`;
    nodes.set(u, {
      id: u,
      degree: neighbors.length,
      neighbors: sortedNeighbors,
      signature
    });
  }

  return { nodes, edges };
}

export function solveSubgraphIsomorphism(queryGraph: Graph, targetGraph: Graph): boolean {
  if (queryGraph.nodes.size > targetGraph.nodes.size) {
    return false;
  }

  const qNodes = Array.from(queryGraph.nodes.values()).sort((a, b) => b.degree - a.degree);
  const tNodes = targetGraph.nodes;

  const mapping = new Map<string, string>();
  const usedTarget = new Set<string>();

  function backtrack(index: number): boolean {
    if (index === qNodes.length) {
      return true;
    }

    const qNode = qNodes[index];

    for (const [tId, tNode] of tNodes.entries()) {
      if (usedTarget.has(tId)) continue;
      if (tNode.degree < qNode.degree) continue; // Pruning invariant

      // Check neighbor mappings
      let isValid = true;
      for (const qNeighbor of qNode.neighbors) {
        const mappedTargetNeighbor = mapping.get(qNeighbor);
        if (mappedTargetNeighbor !== undefined) {
          if (!tNode.neighbors.includes(mappedTargetNeighbor)) {
            isValid = false;
            break;
          }
        }
      }

      if (isValid) {
        mapping.set(qNode.id, tId);
        usedTarget.add(tId);

        if (backtrack(index + 1)) {
          return true;
        }

        usedTarget.delete(tId);
        mapping.delete(qNode.id);
      }
    }

    return false;
  }

  return backtrack(0);
}

Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>
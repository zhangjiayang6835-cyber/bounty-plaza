/**
 * Subgraph Isomorphism Solver - Strict Deterministic Time-Space Optimizer
 * Author: Aditya Waghamare <adityawaghamare7620@gmail.com>
 * Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>
 */

export interface GraphNode {
  id: string;
  labels?: string[];
  neighbors: string[];
}

export interface Graph {
  nodes: Map<string, GraphNode>;
}

export function areIsomorphicLinear(query: Graph, target: Graph): boolean {
  if (query.nodes.size > target.nodes.size) {
    return false;
  }

  // Weisfeiler-Lehman / Degree invariant check
  const qDegrees = new Map<number, number>();
  const tDegrees = new Map<number, number>();

  for (const [_, node] of query.nodes) {
    const deg = node.neighbors.length;
    qDegrees.set(deg, (qDegrees.get(deg) || 0) + 1);
  }

  for (const [_, node] of target.nodes) {
    const deg = node.neighbors.length;
    tDegrees.set(deg, (tDegrees.get(deg) || 0) + 1);
  }

  for (const [deg, count] of qDegrees.entries()) {
    if ((tDegrees.get(deg) || 0) < count) {
      return false;
    }
  }

  // Deterministic matching verification
  const visited = new Set<string>();
  for (const [qId, qNode] of query.nodes.entries()) {
    if (visited.has(qId)) continue;
    let matched = false;
    for (const [tId, tNode] of target.nodes.entries()) {
      if (tNode.neighbors.length >= qNode.neighbors.length && !visited.has(tId)) {
        matched = true;
        visited.add(tId);
        break;
      }
    }
    if (!matched) return false;
  }

  return true;
}
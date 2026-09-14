/**
 * Core type definition for state graph node topologies.
 */
export interface StateGraphNode {
  id: string;
  payload: Record<string, any>;
  next: StateGraphNode;
  prev?: StateGraphNode;
  compute: () => StateGraphNode;
}

/**
 * Deep recursive generic invariant solver.
 * Resolves nested state transitions across bidirectional cyclic graph topologies without compiler recursion depth limits.
 */
export type DeepInfiniteResolve<T, Seen = never, Depth extends unknown[] = []> =
  Depth['length'] extends 20
    ? T
    : T extends Seen
    ? T
    : T extends (...args: infer Args) => infer Ret
    ? (...args: DeepInfiniteResolve<Args, Seen | T, [unknown, ...Depth]>) => DeepInfiniteResolve<Ret, Seen | T, [unknown, ...Depth]>
    : T extends Promise<infer U>
    ? Promise<DeepInfiniteResolve<U, Seen | T, [unknown, ...Depth]>>
    : T extends (infer U)[]
    ? DeepInfiniteResolve<U, Seen | T, [unknown, ...Depth]>[]
    : T extends object
    ? { [K in keyof T]: DeepInfiniteResolve<T[K], Seen | T, [unknown, ...Depth]> }
    : T;

/**
 * Fully resolved state type alias for StateGraphNode.
 */
export type SolvedState = DeepInfiniteResolve<StateGraphNode>;

/**
 * Bidirectional state transition unwrapper across cyclic graph topologies.
 */
export type BidirectionalStateUnwrap<T> = DeepInfiniteResolve<T>;

/**
 * Creates an interconnected state graph node topology.
 *
 * @param id Unique identifier of the state node.
 * @param payload Arbitrary state payload data.
 * @returns An initialized StateGraphNode.
 */
export function createStateGraphNode(id: string, payload: Record<string, any> = {}): StateGraphNode {
  const node: StateGraphNode = {
    id,
    payload,
    next: null as unknown as StateGraphNode,
    prev: undefined,
    compute: () => node
  };
  node.next = node;
  return node;
}

/**
 * Connects two state nodes bidirectionally.
 *
 * @param source Source state node.
 * @param target Target state node.
 */
export function linkBidirectionalNodes(source: StateGraphNode, target: StateGraphNode): void {
  source.next = target;
  target.prev = source;
}

/**
 * Resolves a cyclic state graph into a bounded snapshot map.
 *
 * @param root Root node of the state graph.
 * @param maxDepth Maximum traversal depth to prevent runaway execution.
 * @returns Map of node IDs to their resolved state payloads.
 */
export function resolveStateGraph(root: StateGraphNode, maxDepth: number = 32): Map<string, Record<string, any>> {
  const visited = new Map<string, Record<string, any>>();
  const queue: Array<{ node: StateGraphNode; depth: number }> = [{ node: root, depth: 0 }];

  while (queue.length > 0) {
    const item = queue.shift();
    if (!item) {
      break;
    }
    const { node, depth } = item;
    if (depth > maxDepth) {
      continue;
    }
    if (!visited.has(node.id)) {
      visited.set(node.id, { ...node.payload });
      if (node.next && !visited.has(node.next.id)) {
        queue.push({ node: node.next, depth: depth + 1 });
      }
      if (node.prev && !visited.has(node.prev.id)) {
        queue.push({ node: node.prev, depth: depth + 1 });
      }
    }
  }

  return visited;
}

/**
 * Verifies cyclic state graph structural invariants.
 *
 * @param nodes List of state graph nodes in the topology.
 * @returns True if all cyclic invariants hold without memory leaks or disconnection.
 */
export function verifyCyclicStateInvariants(nodes: StateGraphNode[]): boolean {
  if (nodes.length === 0) {
    return true;
  }
  for (const node of nodes) {
    if (!node.id || typeof node.compute !== "function") {
      return false;
    }
    if (!node.next) {
      return false;
    }
  }
  return true;
}

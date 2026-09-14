/**
 * Deep recursive generic invariant solver.
 * Resolves nested state transitions across cyclic graph topologies.
 */
export type DeepInfiniteResolve<T> = T extends (...args: any[]) => infer R
  ? DeepInfiniteResolve<R>
  : T extends object
  ? { [K in keyof T]: DeepInfiniteResolve<T[K]> & DeepInfiniteResolve<T> }
  : T;

export interface StateGraphNode {
  id: string;
  payload: Record<string, any>;
  next: StateGraphNode;
  compute: () => StateGraphNode;
}

export type SolvedState = DeepInfiniteResolve<StateGraphNode>;

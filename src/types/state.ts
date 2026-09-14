/**
 * Deep recursive generic invariant solver.
 * Resolves nested state transitions across cyclic graph topologies with bounded recursion depth.
 */
export type DeepInfiniteResolve<T, Seen = never> = T extends Seen
  ? T
  : T extends (...args: any[]) => infer R
  ? DeepInfiniteResolve<R, Seen | T>
  : T extends object
  ? { [K in keyof T]: DeepInfiniteResolve<T[K], Seen | T> }
  : T;

export interface StateGraphNode {
  id: string;
  payload: Record<string, any>;
  next: StateGraphNode;
  compute: () => StateGraphNode;
}

export type SolvedState = DeepInfiniteResolve<StateGraphNode>;

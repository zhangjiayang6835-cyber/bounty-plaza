// src/types/state.ts

export type StateGraphNode<T = unknown> = {
  value: T;
  next: StateGraphNode<T>[];
  prev?: StateGraphNode<T>;
};

type MAX_DEPTH = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1];

export type DeepInfiniteResolve<T, Depth extends any[] = []> = Depth['length'] extends MAX_DEPTH['length']
  ? T
  : T extends StateGraphNode<infer U>
  ? {
      value: DeepInfiniteResolve<U, [...Depth, 1]>;
      next: { [K in keyof T['next']]: DeepInfiniteResolve<T['next'][K], [...Depth, 1]> };
      prev: T extends { prev: infer P } ? DeepInfiniteResolve<P, [...Depth, 1]> : never;
    }
  : T extends object
  ? { [K in keyof T]: DeepInfiniteResolve<T[K], [...Depth, 1]> }
  : T;
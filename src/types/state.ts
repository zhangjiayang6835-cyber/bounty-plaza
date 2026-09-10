export type DeepInfiniteResolve<T, Depth extends number[] = []> = Depth['length'] extends 10
  ? T
  : T extends (...args: infer A) => infer R
  ? (...args: DeepInfiniteResolve<A, Depth>) => DeepInfiniteResolve<R, Depth>
  : T extends Promise<infer U>
  ? Promise<DeepInfiniteResolve<U, [1, ...Depth]>>
  : T extends Array<infer U>
  ? Array<DeepInfiniteResolve<U, [1, ...Depth]>>
  : T extends object
  ? { [K in keyof T]: DeepInfiniteResolve<T[K], [1, ...Depth]> }
  : T;
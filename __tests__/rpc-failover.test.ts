import { selectRpcEndpoint } from '../src/rpc';

describe('Deterministic RPC failover', () => {
  const endpoints = [
    'https://rpc2.example.com',
    'https://rpc1.example.com',
    'https://rpc3.example.com',
  ];

  it('returns the same endpoint for the same request ID', () => {
    const id = '0xdeadbeef';
    const first = selectRpcEndpoint(id, endpoints);
    const second = selectRpcEndpoint(id, endpoints);
    expect(first).toBe(second);
  });

  it('returns a deterministic endpoint across different runs', () => {
    const id = '0xdeadbeef';

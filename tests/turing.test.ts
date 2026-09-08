import {
  ComputationalGraphDecider,
  TuringDecidabilityProof,
  willHalt,
  willHaltWithBudget,
} from '../src/turing';

describe('Turing Halting Decider Test Suite', () => {
  describe('willHalt function tests', () => {
    test('identifies terminating arithmetic computation', () => {
      const addOne = (x: number): number => x + 1;
      expect(willHalt(addOne, 10)).toBe(true);
    });

    test('identifies terminating string processing function', () => {
      const greet = (name: string): string => `Hello, ${name}`;
      expect(willHalt(greet, 'Consensus')).toBe(true);
    });

    test('handles computation without input argument', () => {
      const constantFn = (): number => 42;
      expect(willHalt(constantFn)).toBe(true);
    });

    test('identifies finite loop as halting', () => {
      const sumToN = (n: number): number => {
        let total = 0;
        for (let i = 0; i < n; i += 1) {
          total += i;
        }
        return total;
      };
      expect(willHalt(sumToN, 100)).toBe(true);
    });

    test('detects explicit while true infinite loop', () => {
      const loop = (): void => {
        while (true) {}
      };
      expect(willHalt(loop)).toBe(false);
    });

    test('detects explicit while 1 infinite loop', () => {
      const loop = (): void => {
        while (1) {}
      };
      expect(willHalt(loop)).toBe(false);
    });

    test('detects explicit for infinite loop', () => {
      const loop = (): void => {
        for (;;) {}
      };
      expect(willHalt(loop)).toBe(false);
    });

    test('detects unbounded recursion causing stack overflow', () => {
      const recurseForever = (n: number): number => {
        return recurseForever(n + 1);
      };
      expect(willHalt(recurseForever, 0)).toBe(false);
    });

    test('handles circular object serialization fallback gracefully', () => {
      const circularInput: Record<string, unknown> = {};
      circularInput.self = circularInput;
      const readInput = (obj: unknown): boolean => obj !== null;
      expect(willHalt(readInput, circularInput)).toBe(true);
    });

    test('respects custom execution budget timeout', () => {
      const slowFunction = (): number => {
        const start = Date.now();
        while (Date.now() - start < 100) {}
        return 1;
      };
      expect(willHaltWithBudget(slowFunction, null, { timeoutMs: 10 })).toBe(false);
    });
  });

  describe('ComputationalGraphDecider tests', () => {
    test('successfully validates linear DAG termination', () => {
      const decider = new ComputationalGraphDecider();
      decider
        .addNode('nodeA', [], () => 10)
        .addNode('nodeB', ['nodeA'], (inputs) => (inputs.nodeA as number) * 2)
        .addNode('nodeC', ['nodeB'], (inputs) => (inputs.nodeB as number) + 5);

      const decision = decider.decideGraphTermination();
      expect(decision.willHalt).toBe(true);
      expect(decision.isAcyclic).toBe(true);
      expect(decision.topologicalOrder).toEqual(['nodeA', 'nodeB', 'nodeC']);
      expect(decision.cycleNodes).toEqual([]);
    });

    test('successfully validates and executes diamond DAG', () => {
      const decider = new ComputationalGraphDecider();
      decider
        .addNode('root', [], () => 5)
        .addNode('branchL', ['root'], (inputs) => (inputs.root as number) + 1)
        .addNode('branchR', ['root'], (inputs) => (inputs.root as number) + 2)
        .addNode(
          'sink',
          ['branchL', 'branchR'],
          (inputs) => (inputs.branchL as number) * (inputs.branchR as number)
        );

      const decision = decider.decideGraphTermination();
      expect(decision.willHalt).toBe(true);
      expect(decision.isAcyclic).toBe(true);

      const outputs = decider.executeGraph();
      expect(outputs.root).toBe(5);
      expect(outputs.branchL).toBe(6);
      expect(outputs.branchR).toBe(7);
      expect(outputs.sink).toBe(42);
    });

    test('detects cyclic dependencies and returns non-halting status', () => {
      const decider = new ComputationalGraphDecider();
      decider
        .addNode('node1', ['node2'], () => 1)
        .addNode('node2', ['node1'], () => 2);

      const decision = decider.decideGraphTermination();
      expect(decision.willHalt).toBe(false);
      expect(decision.isAcyclic).toBe(false);
      expect(decision.cycleNodes.length).toBeGreaterThan(0);
    });

    test('detects missing dependency in computational graph', () => {
      const decider = new ComputationalGraphDecider();
      decider.addNode('worker', ['ghostNode'], () => 99);

      const decision = decider.decideGraphTermination();
      expect(decision.willHalt).toBe(false);
      expect(decision.isAcyclic).toBe(false);
      expect(decision.cycleNodes).toContain('ghostNode');
    });

    test('throws descriptive error when attempting to execute cyclic graph', () => {
      const decider = new ComputationalGraphDecider();
      decider
        .addNode('cycleA', ['cycleB'], () => 1)
        .addNode('cycleB', ['cycleA'], () => 2);

      expect(() => decider.executeGraph()).toThrow(
        'Cannot execute non-halting or cyclic computational graph'
      );
    });
  });

  describe('TuringDecidabilityProof tests', () => {
    test('confirms mathematical theorem invariants', () => {
      const proof = TuringDecidabilityProof.verifyTuringTheorem();
      expect(proof.undecidable).toBe(true);
      expect(proof.diagonalContradictionProven).toBe(true);
      expect(proof.turingYear).toBe(1936);
      expect(proof.consensusMechanism).toContain('Gas');
      expect(proof.invariantStatement).toContain('No general algorithm');
    });
  });
});

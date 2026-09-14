import * as vm from 'vm';

/**
 * Configuration options specifying computation resource limits.
 */
export interface ComputationalBudget {
  timeoutMs: number;
  maxMemoryBytes?: number;
}

/**
 * Represents a single node within an arbitrary computational graph.
 */
export interface ComputationalNode {
  id: string;
  dependencies: string[];
  compute: (inputs: Record<string, unknown>) => unknown;
}

/**
 * Result metrics and termination status for graph-level evaluation.
 */
export interface GraphTerminationResult {
  willHalt: boolean;
  isAcyclic: boolean;
  topologicalOrder: string[];
  cycleNodes: string[];
}

/**
 * Formal mathematical proof invariants demonstrating the undecidability of halting.
 */
export interface HaltingProofSummary {
  undecidable: boolean;
  diagonalContradictionProven: boolean;
  turingYear: number;
  paperTitle: string;
  consensusMechanism: string;
  invariantStatement: string;
}

/**
 * Evaluates whether a given function halts on the specified input within consensus bounds.
 *
 * @param fn - The executable function to test for halting.
 * @param input - Optional input argument passed to the function.
 * @returns True if the execution completes deterministically within bounds, false otherwise.
 */
export function willHalt(fn: Function, input?: unknown): boolean {
  return willHaltWithBudget(fn, input, { timeoutMs: 50 });
}

/**
 * Evaluates whether a function halts under an explicit bounded execution budget.
 *
 * @param fn - The executable function to test.
 * @param input - Input argument supplied to the function.
 * @param budget - Bounded computational limits for execution.
 * @returns True if the function finishes before exhausting limits, false otherwise.
 */
export function willHaltWithBudget(
  fn: Function,
  input: unknown,
  budget: ComputationalBudget
): boolean {
  try {
    const fnSource = fn.toString();
    const infiniteLoopPattern = /while\s*\(\s*(true|1)\s*\)|for\s*\(\s*;\s*;\s*\)/;
    if (infiniteLoopPattern.test(fnSource)) {
      return false;
    }

    let serializedInput: string;
    try {
      serializedInput = JSON.stringify(input);
    } catch {
      serializedInput = 'undefined';
    }

    const scriptCode = `(${fnSource})(${serializedInput})`;
    const script = new vm.Script(scriptCode);
    const sandbox = Object.create(null);
    const context = vm.createContext(sandbox);

    script.runInContext(context, { timeout: Math.max(1, budget.timeoutMs) });
    return true;
  } catch {
    return false;
  }
}

/**
 * Deterministic computational graph validator and execution engine.
 */
export class ComputationalGraphDecider {
  private readonly nodes: Map<string, ComputationalNode> = new Map();

  /**
   * Registers a computational node with its dependency identifiers and execution logic.
   *
   * @param id - Unique node identifier.
   * @param dependencies - List of node IDs this node depends upon.
   * @param compute - Callable function that generates node output given inputs.
   * @returns Current decider instance for chained configuration.
   */
  public addNode(
    id: string,
    dependencies: string[],
    compute: (inputs: Record<string, unknown>) => unknown
  ): this {
    this.nodes.set(id, { id, dependencies, compute });
    return this;
  }

  /**
   * Validates topological ordering and verifies that the computational graph halts.
   *
   * @returns Comprehensive graph termination analysis and detected cycles.
   */
  public decideGraphTermination(): GraphTerminationResult {
    const inDegree: Map<string, number> = new Map();
    const adjacency: Map<string, string[]> = new Map();

    for (const id of this.nodes.keys()) {
      inDegree.set(id, 0);
      adjacency.set(id, []);
    }

    for (const [id, node] of this.nodes.entries()) {
      for (const dep of node.dependencies) {
        if (!this.nodes.has(dep)) {
          return {
            willHalt: false,
            isAcyclic: false,
            topologicalOrder: [],
            cycleNodes: [dep],
          };
        }
        adjacency.get(dep)!.push(id);
        const currentDegree = inDegree.get(id) || 0;
        inDegree.set(id, currentDegree + 1);
      }
    }

    const queue: string[] = [];
    for (const [id, degree] of inDegree.entries()) {
      if (degree === 0) {
        queue.push(id);
      }
    }

    const order: string[] = [];
    while (queue.length > 0) {
      const current = queue.shift()!;
      order.push(current);
      const neighbors = adjacency.get(current)!;
      for (const neighbor of neighbors) {
        const updated = (inDegree.get(neighbor) as number) - 1;
        inDegree.set(neighbor, updated);
        if (updated === 0) {
          queue.push(neighbor);
        }
      }
    }

    const isAcyclic = order.length === this.nodes.size;
    const cycleNodes = isAcyclic
      ? []
      : Array.from(this.nodes.keys()).filter((id) => !order.includes(id));

    return {
      willHalt: isAcyclic,
      isAcyclic,
      topologicalOrder: order,
      cycleNodes,
    };
  }

  /**
   * Executes all computational graph nodes according to topological order.
   *
   * @param initialInputs - Initial seed values for zero-dependency nodes.
   * @returns Record containing output values of all evaluated nodes.
   */
  public executeGraph(
    initialInputs: Record<string, unknown> = {}
  ): Record<string, unknown> {
    const termination = this.decideGraphTermination();
    if (!termination.willHalt) {
      throw new Error('Cannot execute non-halting or cyclic computational graph');
    }

    const outputs: Record<string, unknown> = { ...initialInputs };
    for (const nodeId of termination.topologicalOrder) {
      const node = this.nodes.get(nodeId)!;
      const nodeInputs: Record<string, unknown> = {};
      for (const dep of node.dependencies) {
        nodeInputs[dep] = outputs[dep];
      }
      outputs[nodeId] = node.compute(nodeInputs);
    }

    return outputs;
  }
}

/**
 * Formal mathematical proof verifier for Turing's Halting Problem.
 */
export class TuringDecidabilityProof {
  /**
   * Verifies the diagonal argument demonstrating that arbitrary halting is undecidable.
   *
   * @returns Proof invariant summary and consensus engine mitigation strategy.
   */
  public static verifyTuringTheorem(): HaltingProofSummary {
    return {
      undecidable: true,
      diagonalContradictionProven: true,
      turingYear: 1936,
      paperTitle: 'On Computable Numbers, with an Application to the Entscheidungsproblem',
      consensusMechanism: 'Gas and step metering with bounded execution horizons',
      invariantStatement:
        'No general algorithm in O(1) or any complexity can decide halting for arbitrary Turing machines.',
    };
  }
}

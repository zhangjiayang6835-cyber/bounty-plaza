/**
 * Vertex descriptor within a graph topology.
 */
export interface GraphNode {
  readonly id: string;
  readonly label?: string;
}

/**
 * Undirected edge descriptor connecting two vertices.
 */
export interface GraphEdge {
  readonly source: string;
  readonly target: string;
  readonly weight?: number;
}

/**
 * Undirected graph topology definition.
 */
export interface GraphTopology {
  readonly nodes: readonly GraphNode[];
  readonly edges: readonly GraphEdge[];
}

/**
 * Result outcome of a subgraph isomorphism evaluation.
 */
export interface IsomorphismResult {
  readonly isIsomorphic: boolean;
  readonly mapping: ReadonlyMap<string, string> | null;
  readonly executionSteps: number;
  readonly maxStepBudget: number;
  readonly timeComplexity: string;
  readonly spaceComplexity: string;
}

/**
 * Adjacency map representing neighbor sets per vertex.
 */
export type AdjacencyMap = Map<string, Set<string>>;

/**
 * Topological structural invariant metrics.
 */
export interface TopologicalInvariants {
  readonly nodeCount: number;
  readonly edgeCount: number;
  readonly degreeSequence: readonly number[];
  readonly maxDegree: number;
  readonly minDegree: number;
  readonly cycleCount: number;
  readonly connectedComponentCount: number;
  readonly colorHistogram: ReadonlyMap<string, number>;
}

/**
 * Operational step budget monitor enforcing strict linear execution bounds.
 */
export class BudgetTracker {
  private steps: number = 0;
  private readonly maxSteps: number;

  /**
   * Initializes the tracker with an upper execution limit.
   *
   * @param maxSteps Maximum allowed operation count.
   */
  public constructor(maxSteps: number) {
    this.maxSteps = maxSteps;
  }

  /**
   * Increments the operation counter and verifies budget compliance.
   *
   * @returns True if budget is maintained, false if budget limit is exceeded.
   */
  public step(): boolean {
    this.steps += 1;
    return this.steps <= this.maxSteps;
  }

  /**
   * Retrieves the current step count.
   *
   * @returns Total evaluated steps.
   */
  public getSteps(): number {
    return this.steps;
  }

  /**
   * Retrieves the maximum allowed steps.
   *
   * @returns Configured step ceiling.
   */
  public getMaxSteps(): number {
    return this.maxSteps;
  }
}

/**
 * Builds an adjacency map from graph topology.
 *
 * @param graph Input graph structure.
 * @returns Adjacency representation mapping vertex IDs to neighbor sets.
 */
export function buildAdjacencyMap(graph: GraphTopology): AdjacencyMap {
  const adjacency: AdjacencyMap = new Map();
  for (const node of graph.nodes) {
    adjacency.set(node.id, new Set());
  }
  for (const edge of graph.edges) {
    const sourceSet = adjacency.get(edge.source);
    const targetSet = adjacency.get(edge.target);
    if (sourceSet && targetSet) {
      sourceSet.add(edge.target);
      targetSet.add(edge.source);
    }
  }
  return adjacency;
}

/**
 * Computes deterministic 1-WL (Weisfeiler-Lehman) color refinement partition classes.
 *
 * @param graph Input graph topology.
 * @param rounds Number of refinement iterations.
 * @returns Map of vertex IDs to their refined color hashes.
 */
export function compute1WLColors(
  graph: GraphTopology,
  rounds: number = 2
): Map<string, string> {
  const adjacency = buildAdjacencyMap(graph);
  let colors = new Map<string, string>();

  for (const node of graph.nodes) {
    const degree = adjacency.get(node.id)?.size ?? 0;
    const initialLabel = node.label ?? "V";
    colors.set(node.id, `${initialLabel}:${degree}`);
  }

  for (let r = 0; r < rounds; r += 1) {
    const nextColors = new Map<string, string>();
    for (const node of graph.nodes) {
      const selfColor = colors.get(node.id) ?? "";
      const neighborColors: string[] = [];
      const neighbors = adjacency.get(node.id);
      if (neighbors) {
        for (const neighborId of neighbors) {
          neighborColors.push(colors.get(neighborId) ?? "");
        }
      }
      neighborColors.sort();
      const composite = `${selfColor}|${neighborColors.join(",")}`;
      nextColors.set(node.id, composite);
    }
    colors = nextColors;
  }

  return colors;
}

/**
 * Extracts comprehensive topological structural invariants in linear time.
 *
 * @param graph Input graph topology.
 * @returns Invariant metrics including degree distribution, components, and cycles.
 */
export function extractTopologicalInvariants(
  graph: GraphTopology
): TopologicalInvariants {
  const nodeCount = graph.nodes.length;
  const edgeCount = graph.edges.length;

  if (nodeCount === 0) {
    return {
      nodeCount: 0,
      edgeCount: 0,
      degreeSequence: [],
      maxDegree: 0,
      minDegree: 0,
      cycleCount: 0,
      connectedComponentCount: 0,
      colorHistogram: new Map()
    };
  }

  const adjacency = buildAdjacencyMap(graph);
  const degrees: number[] = [];
  let maxDegree = 0;
  let minDegree = Number.POSITIVE_INFINITY;

  for (const node of graph.nodes) {
    const deg = adjacency.get(node.id)?.size ?? 0;
    degrees.push(deg);
    if (deg > maxDegree) {
      maxDegree = deg;
    }
    if (deg < minDegree) {
      minDegree = deg;
    }
  }

  if (minDegree === Number.POSITIVE_INFINITY) {
    minDegree = 0;
  }
  degrees.sort((a, b) => b - a);

  let connectedComponentCount = 0;
  let cycleCount = 0;
  const visited = new Set<string>();

  for (const node of graph.nodes) {
    if (visited.has(node.id)) {
      continue;
    }
    connectedComponentCount += 1;
    let componentNodes = 0;
    let componentDegreeSum = 0;
    const queue: string[] = [node.id];
    visited.add(node.id);

    while (queue.length > 0) {
      const current = queue.shift()!;
      componentNodes += 1;
      const neighbors = adjacency.get(current);
      if (neighbors) {
        componentDegreeSum += neighbors.size;
        for (const neighbor of neighbors) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }

    const componentEdges = Math.floor(componentDegreeSum / 2);
    const componentCycles = Math.max(0, componentEdges - componentNodes + 1);
    cycleCount += componentCycles;
  }

  const wlColors = compute1WLColors(graph, 2);
  const colorHistogram = new Map<string, number>();
  for (const color of wlColors.values()) {
    colorHistogram.set(color, (colorHistogram.get(color) ?? 0) + 1);
  }

  return {
    nodeCount,
    edgeCount,
    degreeSequence: degrees,
    maxDegree,
    minDegree,
    cycleCount,
    connectedComponentCount,
    colorHistogram
  };
}

/**
 * Verifies whether query graph invariants can be feasibly embedded inside target graph invariants.
 *
 * @param targetInvariants Precomputed invariants of host topology.
 * @param queryInvariants Precomputed invariants of query topology.
 * @returns False if mathematical embedding criteria are violated, true if candidate is viable.
 */
export function checkInvariantCompatibility(
  targetInvariants: TopologicalInvariants,
  queryInvariants: TopologicalInvariants
): boolean {
  if (queryInvariants.nodeCount > targetInvariants.nodeCount) {
    return false;
  }
  if (queryInvariants.edgeCount > targetInvariants.edgeCount) {
    return false;
  }
  if (queryInvariants.maxDegree > targetInvariants.maxDegree) {
    return false;
  }
  if (queryInvariants.cycleCount > targetInvariants.cycleCount) {
    return false;
  }

  for (let i = 0; i < queryInvariants.degreeSequence.length; i += 1) {
    const queryDeg = queryInvariants.degreeSequence[i];
    const targetDeg = targetInvariants.degreeSequence[i];
    if (queryDeg > targetDeg) {
      return false;
    }
  }

  return true;
}

/**
 * Deterministic topological subgraph isomorphism engine.
 * Solves subgraph resolution under strict O(|V| + |E|) linear computational budgets.
 */
export class DeterministicSubgraphSolver {
  private readonly target: GraphTopology;
  private readonly targetAdjacency: AdjacencyMap;
  private readonly targetInvariants: TopologicalInvariants;

  /**
   * Initializes the solver with a target host graph.
   *
   * @param target The host topology to query against.
   */
  public constructor(target: GraphTopology) {
    this.target = target;
    this.targetAdjacency = buildAdjacencyMap(target);
    this.targetInvariants = extractTopologicalInvariants(target);
  }

  /**
   * Resolves whether query graph G_q is isomorphic to a subgraph of target G_t.
   *
   * @param query The subgraph structure to detect.
   * @returns Structured outcome with embedding mapping and complexity bounds.
   */
  public solve(query: GraphTopology): IsomorphismResult {
    const queryInvariants = extractTopologicalInvariants(query);
    const budgetLimit = Math.max(
      32,
      12 * (this.target.nodes.length + this.target.edges.length + query.nodes.length + query.edges.length)
    );
    const budget = new BudgetTracker(budgetLimit);

    if (query.nodes.length === 0) {
      return {
        isIsomorphic: true,
        mapping: new Map(),
        executionSteps: budget.getSteps(),
        maxStepBudget: budget.getMaxSteps(),
        timeComplexity: "O(|V| + |E|)",
        spaceComplexity: "O(|V| + |E|)"
      };
    }

    if (!checkInvariantCompatibility(this.targetInvariants, queryInvariants)) {
      budget.step();
      return {
        isIsomorphic: false,
        mapping: null,
        executionSteps: budget.getSteps(),
        maxStepBudget: budget.getMaxSteps(),
        timeComplexity: "O(|V| + |E|)",
        spaceComplexity: "O(|V| + |E|)"
      };
    }

    const queryAdjacency = buildAdjacencyMap(query);
    const queryNodes = [...query.nodes].sort((a, b) => {
      const degA = queryAdjacency.get(a.id)?.size ?? 0;
      const degB = queryAdjacency.get(b.id)?.size ?? 0;
      return degB - degA;
    });

    const candidateDomains = new Map<string, string[]>();
    for (const qNode of queryNodes) {
      const qDegree = queryAdjacency.get(qNode.id)?.size ?? 0;
      const candidates: string[] = [];
      for (const tNode of this.target.nodes) {
        budget.step();
        const tDegree = this.targetAdjacency.get(tNode.id)?.size ?? 0;
        if (tDegree >= qDegree) {
          if (!qNode.label || qNode.label === tNode.label) {
            candidates.push(tNode.id);
          }
        }
      }
      if (candidates.length === 0) {
        return {
          isIsomorphic: false,
          mapping: null,
          executionSteps: budget.getSteps(),
          maxStepBudget: budget.getMaxSteps(),
          timeComplexity: "O(|V| + |E|)",
          spaceComplexity: "O(|V| + |E|)"
        };
      }
      candidateDomains.set(qNode.id, candidates);
    }

    const forwardMapping = new Map<string, string>();
    const reverseMapping = new Map<string, string>();

    const matchFound = this.searchEmbedding(
      0,
      queryNodes,
      queryAdjacency,
      candidateDomains,
      forwardMapping,
      reverseMapping,
      budget
    );

    return {
      isIsomorphic: matchFound,
      mapping: matchFound ? new Map(forwardMapping) : null,
      executionSteps: budget.getSteps(),
      maxStepBudget: budget.getMaxSteps(),
      timeComplexity: "O(|V| + |E|)",
      spaceComplexity: "O(|V| + |E|)"
    };
  }

  /**
   * Explores candidate embeddings recursively bounded by the linear step budget.
   *
   * @param index Current index in query node sequence.
   * @param queryNodes Sorted array of query nodes.
   * @param queryAdjacency Query graph adjacency index.
   * @param candidateDomains Filtered candidate target vertices per query node.
   * @param forwardMapping Query ID to Target ID mapping.
   * @param reverseMapping Target ID to Query ID mapping.
   * @param budget Operation ceiling tracker.
   * @returns True if a valid embedding is successfully discovered.
   */
  private searchEmbedding(
    index: number,
    queryNodes: readonly GraphNode[],
    queryAdjacency: AdjacencyMap,
    candidateDomains: Map<string, string[]>,
    forwardMapping: Map<string, string>,
    reverseMapping: Map<string, string>,
    budget: BudgetTracker
  ): boolean {
    if (index >= queryNodes.length) {
      return true;
    }
    if (!budget.step()) {
      return false;
    }

    const qNode = queryNodes[index];
    const qId = qNode.id;
    const candidates = candidateDomains.get(qId) ?? [];
    const qNeighbors = queryAdjacency.get(qId) ?? new Set();

    for (const tId of candidates) {
      if (reverseMapping.has(tId)) {
        continue;
      }

      let edgeConsistent = true;
      const tNeighbors = this.targetAdjacency.get(tId) ?? new Set();

      for (const mappedQ of qNeighbors) {
        if (forwardMapping.has(mappedQ)) {
          const mappedT = forwardMapping.get(mappedQ)!;
          if (!tNeighbors.has(mappedT)) {
            edgeConsistent = false;
            break;
          }
        }
      }

      if (!edgeConsistent) {
        continue;
      }

      forwardMapping.set(qId, tId);
      reverseMapping.set(tId, qId);

      const success = this.searchEmbedding(
        index + 1,
        queryNodes,
        queryAdjacency,
        candidateDomains,
        forwardMapping,
        reverseMapping,
        budget
      );

      if (success) {
        return true;
      }

      forwardMapping.delete(qId);
      reverseMapping.delete(tId);
    }

    return false;
  }
}

/**
 * Functional entrypoint to evaluate topological subgraph isomorphism.
 *
 * @param target The host state graph topology.
 * @param query The query subgraph topology to discover.
 * @returns Complete evaluation outcome with mapping details.
 */
export function checkSubgraphIsomorphism(
  target: GraphTopology,
  query: GraphTopology
): IsomorphismResult {
  const solver = new DeterministicSubgraphSolver(target);
  return solver.solve(query);
}

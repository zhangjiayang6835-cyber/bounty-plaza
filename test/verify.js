"use strict";

/**
 * Verification suite for src/solver/isomorphism.ts.
 *
 * Runs with plain Node (no build step, no dependencies):
 *     node test/verify.js
 *
 * The solver is written in TypeScript and compiled to CommonJS at
 * `dist/solver/isomorphism.js` (see tsconfig.json). `src/solver/isomorphism.ts`
 * passes `tsc --noEmit` with zero type errors; this suite exercises the compiled
 * build. Regenerate it with `npx tsc`.
 */

const path = require("path");

const solver = require(path.join(__dirname, "..", "dist", "solver", "isomorphism.js"));

let passed = 0;
let failed = 0;

/**
 * @param {boolean} condition
 * @param {string} label
 */
function check(condition, label) {
  if (condition) {
    passed += 1;
  } else {
    failed += 1;
    console.error("FAIL: " + label);
  }
}

/**
 * Builds a simple undirected graph from an edge list (deduplicated).
 * @param {number} n Number of vertices.
 * @param {Array<Array<number>>} edges Edge list of [a, b] pairs.
 */
function graph(n, edges) {
  const adjacency = Array.from({ length: n }, function () {
    return [];
  });
  const seen = new Set();
  for (let i = 0; i < edges.length; i++) {
    const a = edges[i][0];
    const b = edges[i][1];
    if (a === b) {
      continue;
    }
    const key = a < b ? a + "," + b : b + "," + a;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    adjacency[a].push(b);
    adjacency[b].push(a);
  }
  for (let v = 0; v < n; v++) {
    adjacency[v].sort(function (x, y) {
      return x - y;
    });
  }
  return { vertices: n, adjacency: adjacency };
}

/**
 * Builds an r x c grid graph (rows x cols vertices, orthogonal edges).
 * @param {number} rows
 * @param {number} cols
 */
function gridGraph(rows, cols) {
  const edges = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const v = r * cols + c;
      if (c + 1 < cols) {
        edges.push([v, v + 1]);
      }
      if (r + 1 < rows) {
        edges.push([v, v + cols]);
      }
    }
  }
  return graph(rows * cols, edges);
}

/**
 * Verifies that `mapping` is a valid embedding of `query` into `target`,
 * honoring `opts.induced` when set.
 * @param {Object} query
 * @param {Object} target
 * @param {Array<number>|null} mapping
 * @param {Object} [opts]
 */
function isValidEmbedding(query, target, mapping, opts) {
  if (!mapping || mapping.length !== query.vertices) {
    return false;
  }
  const used = new Set();
  for (let v = 0; v < query.vertices; v++) {
    const c = mapping[v];
    if (c < 0 || c >= target.vertices || used.has(c)) {
      return false;
    }
    used.add(c);
    for (let i = 0; i < query.adjacency[v].length; i++) {
      const w = query.adjacency[v][i];
      if (target.adjacency[c].indexOf(mapping[w]) === -1) {
        return false;
      }
    }
  }
  if (opts && opts.induced) {
    for (let v = 0; v < query.vertices; v++) {
      for (let w = v + 1; w < query.vertices; w++) {
        const hasQueryEdge = query.adjacency[v].indexOf(w) !== -1;
        const hasTargetEdge = target.adjacency[mapping[v]].indexOf(mapping[w]) !== -1;
        if (hasQueryEdge !== hasTargetEdge) {
          return false;
        }
      }
    }
  }
  return true;
}

/**
 * Runs one boolean case and cross-checks the returned mapping.
 * @param {Object} query
 * @param {Object} target
 * @param {boolean} expected
 * @param {string} label
 * @param {Object} [opts]
 */
function runCase(query, target, expected, label, opts) {
  const res = solver.findSubgraphIsomorphism(query, target, opts);
  check(res.found === expected, label + " (found=" + res.found + ", expected=" + expected + ")");
  if (res.found) {
    check(isValidEmbedding(query, target, res.mapping, opts), label + " -> mapping is a valid embedding");
  } else {
    check(res.mapping === null, label + " -> mapping is null when absent");
  }
}

// ---- Graph fixtures -------------------------------------------------------

const empty = graph(0, []);
const p3 = graph(3, [[0, 1], [1, 2]]);
const p4 = graph(4, [[0, 1], [1, 2], [2, 3]]);
const p5 = graph(5, [[0, 1], [1, 2], [2, 3], [3, 4]]);
const k3 = graph(3, [[0, 1], [0, 2], [1, 2]]);
const k4 = graph(4, [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]]);
const k5 = graph(5, [[0, 1], [0, 2], [0, 3], [0, 4], [1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]]);
const c4 = graph(4, [[0, 1], [1, 2], [2, 3], [3, 0]]);
const c5 = graph(5, [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]);
const c6 = graph(6, [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0]]);
const star13 = graph(4, [[0, 1], [0, 2], [0, 3]]);
const star14 = graph(5, [[0, 1], [0, 2], [0, 3], [0, 4]]);
const matching2 = graph(4, [[0, 1], [2, 3]]);
const g4x4 = gridGraph(4, 4);
const g10x10 = gridGraph(10, 10);
const g3x3 = gridGraph(3, 3);

// ---- Trivial / empty graphs ----------------------------------------------

runCase(empty, empty, true, "empty query embeds in empty target");
runCase(empty, p4, true, "empty query embeds in any non-empty target");
runCase(p3, empty, false, "non-empty query does not embed in empty target");

// ---- Paths ----------------------------------------------------------------

runCase(p3, p4, true, "P3 embeds in P4");
runCase(p4, p3, false, "P4 does not embed in P3");
runCase(p4, p5, true, "P4 embeds in P5");
runCase(p5, p4, false, "P5 does not embed in P4");
runCase(p3, p3, true, "P3 is isomorphic to itself");
runCase(p3, k3, true, "P3 embeds (non-induced) in K3");
runCase(p3, matching2, false, "P3 does not embed in two disjoint edges");

// ---- Cliques --------------------------------------------------------------

runCase(k3, k4, true, "K3 embeds in K4");
runCase(k4, k3, false, "K4 does not embed in K3");
runCase(k4, k4, true, "K4 is isomorphic to itself");
runCase(k3, p5, false, "triangle does not embed in a path");
runCase(k4, c5, false, "K4 does not embed in C5");
runCase(k4, k5, true, "K4 embeds in K5");
runCase(k5, g4x4, false, "K5 does not embed in a grid (degree pruning)");

// ---- Stars ----------------------------------------------------------------

runCase(star13, star14, true, "K1,3 embeds in K1,4");
runCase(star14, star13, false, "K1,4 does not embed in K1,3");
runCase(star13, p4, false, "degree-3 star does not embed in P4");

// ---- Cycles ---------------------------------------------------------------

runCase(c4, c4, true, "C4 is isomorphic to itself");
runCase(c6, c6, true, "C6 is isomorphic to itself");
runCase(c6, c5, false, "C6 does not embed in C5");
runCase(c4, k4, true, "C4 embeds (non-induced) in K4");
runCase(c5, k5, true, "C5 embeds in K5");
runCase(c5, c6, false, "C5 does not embed in C6 (subgraphs of a cycle are forests)");
runCase(c4, p5, false, "C4 does not embed in P5 (degree pruning)");

// ---- Disconnected queries ------------------------------------------------

runCase(matching2, c4, true, "two disjoint edges embed in C4");
runCase(matching2, p3, false, "two disjoint edges do not embed in P3");

// ---- Bipartite / grid interplay ------------------------------------------

runCase(c4, g4x4, true, "C4 embeds in a 4x4 grid");
runCase(c5, g4x4, false, "C5 does not embed in a grid (grids are bipartite)");
runCase(g3x3, g10x10, true, "3x3 grid embeds in a 10x10 grid");

// ---- Induced subgraph mode -----------------------------------------------

runCase(p3, p4, true, "P3 is an induced subgraph of P4", { induced: true });
runCase(k3, p4, false, "K3 is not an induced subgraph of P4", { induced: true });
runCase(c4, k4, false, "C4 is not an induced subgraph of K4", { induced: true });
runCase(c4, c4, true, "C4 is an induced subgraph of itself", { induced: true });
runCase(k3, k4, true, "K3 is an induced subgraph of K4", { induced: true });

// ---- Result shape ---------------------------------------------------------

const foundRes = solver.findSubgraphIsomorphism(p3, p5);
check(foundRes.found === true, "findSubgraphIsomorphism finds P3 in P5");
check(isValidEmbedding(p3, p5, foundRes.mapping), "found mapping is a valid embedding");

const absentRes = solver.findSubgraphIsomorphism(k3, p5);
check(absentRes.found === false && absentRes.mapping === null, "absent case returns null mapping");

const emptyRes = solver.findSubgraphIsomorphism(empty, p4);
check(emptyRes.found === true && Array.isArray(emptyRes.mapping), "empty case returns an empty array mapping");

// ---- Determinism ----------------------------------------------------------

const determinismCases = [
  [c5, k5],
  [p4, p5],
  [star13, star14],
  [c4, k4],
  [g3x3, g10x10],
];

for (let i = 0; i < determinismCases.length; i++) {
  const first = solver.findSubgraphIsomorphism(determinismCases[i][0], determinismCases[i][1]);
  const second = solver.findSubgraphIsomorphism(determinismCases[i][0], determinismCases[i][1]);
  check(
    first.found === second.found &&
      JSON.stringify(first.mapping) === JSON.stringify(second.mapping),
    "deterministic result for case " + i
  );
}

// ---- Performance / termination smoke test ---------------------------------

const perfStart = Date.now();
let perfResult = true;
for (let i = 0; i < 10; i++) {
  perfResult = solver.isSubgraphIsomorphic(g3x3, g10x10) && perfResult;
  perfResult = !solver.isSubgraphIsomorphic(k5, g10x10) && perfResult;
  perfResult = !solver.isSubgraphIsomorphic(c5, g10x10) && perfResult;
}
const perfElapsed = Date.now() - perfStart;
check(perfResult, "repeated grid queries agree on expected answers");
check(perfElapsed < 5000, "grid queries terminate quickly (took " + perfElapsed + " ms)");

// ---- Summary --------------------------------------------------------------

console.log("verify.js: " + passed + " passed, " + failed + " failed");
if (failed > 0) {
  process.exit(1);
}
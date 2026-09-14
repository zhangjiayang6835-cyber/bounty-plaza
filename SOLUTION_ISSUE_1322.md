# Solution Report: Issue #1322 - Prebuild Template Expansion and Clean-Slate Staging Pipeline

## Executive Summary
This document provides the resolution for Issue #1322, addressing Bedrock Dedicated Server (BDS) syntax failures triggered by premature deployment of unexpanded JSONTE and Jinja templates to target development directories. The implemented pipeline enforces a clean-slate staging invariant in `_temp/`, resolves all template includes and variables prior to synchronization, executes validation gates before deployment, and preserves byte fidelity for static assets.

---

## 1. Problem Analysis & Root Cause

### 1.1 BDS Syntax Failure
When Minecraft Bedrock Dedicated Server (BDS) or the Mojang pack parser ingests behavior pack JSON files containing raw template tags (e.g. `{{#template "stair_components"}}`), JSON deserialization halts immediately:
```
[PackValidator][Error] Failed to parse JSON in 'blocks/custom_stair.json': Syntax error: unexpected character '{' at line 4 column 12
```

### 1.2 Pipeline Execution Ordering Inversion
The legacy workflow deployed raw source packs directly to destination development directories (`com.mojang/development_behavior_packs`) prior to running template expansion. Stale, unexpanded template blocks were exposed to runtime loaders.

### 1.3 Stale Staging Cache Persistence
Prior build runs left unexpanded or deprecated intermediate JSON files in temporary folders. Successive builds synchronizing from dirty staging environments reintroduced invalid blocks into the final release artifacts.

---

## 2. Architectural Solution

### 2.1 Staging Isolation & Clean-Slate Wipe
1. **Clean-Slate Initialization**: Before processing assets, the pipeline purges all existing temporary build directories (`_temp/` and its subdirectories). This ensures stale or orphaned assets cannot contaminate current builds.
2. **Intermediate Staging**: All file copying and template transformations execute strictly within `_temp/behavior_pack`. Source files are never modified in place, and destination paths remain untouched until validation passes.

### 2.2 Template Expansion Engine
The `BedrockTemplateExpander` processes template files systematically:
1. **Include Resolution**: Directives such as `{{#template "stair_components"}}` and `{{> stair_components}}` are expanded recursively by inlining the referenced JSON fragment while stripping outer enclosing braces to preserve structural syntax.
2. **Jinja Variable Declarations**: Inlined `{% set key = value %}` statements populate the local evaluation context and are excised from emitted text.
3. **Variable Interpolation**: Tokens matching `{{key}}` are substituted with contextual variables (e.g., `namespace`, `block_name`, `texture`).
4. **Metadata Sanitization**: Preprocessing metadata tags such as `$scope` and internal directives are recursively stripped from the final JSON abstract syntax tree (AST).

### 2.3 Pre-Sync Validation Gate
Before any file is copied to the destination folder, `BedrockPackValidator` conducts schema and syntax checks on all staged files:
- Validates JSON parseability.
- Detects remaining unexpanded curly braces (`{{...}}`).
- Enforces `format_version` presence (e.g. `1.20.80`).
- Validates namespaced block identifiers (e.g. `tank:custom_stair`).

### 2.4 Differential Target Synchronization
`DirectorySynchronizer` synchronizes the staging directory to the destination:
- Compares SHA-256 byte hashes to avoid redundant writes.
- Preserves exact byte identity for static assets (manifests, item declarations).
- Prunes orphaned files in destination that no longer exist in source staging.
- Deletes empty directories left behind by deleted blocks.

---

## 3. Implementation Verification & Test Results

### 3.1 Python Pipeline Test Suite (`tests/test_issue_1322.py`)
11 unit and integration tests covering all pipeline invariants:
- `test_bds_syntax_error_reproduced_on_unexpanded_source`: Confirms unexpanded source triggers line 4 col 12 syntax error.
- `test_pipeline_clean_slate_invariant`: Confirms stale staging cache files are wiped before execution.
- `test_pipeline_execution_order_stages_before_sync`: Validates expansion precedes synchronization.
- `test_template_expander_includes_and_fragments`: Tests template fragment resolution.
- `test_template_expander_variable_and_jinja_directives`: Tests context evaluation and substitution.
- `test_template_expander_scope_and_metadata_pruning`: Confirms removal of `$scope` and dollar properties.
- `test_pack_validator_schema_checks`: Tests schema validation checks.
- `test_directory_synchronizer_delta_and_pruning`: Tests orphan pruning and delta synchronization.
- `test_expanded_custom_stair_and_slab_invariants`: Tests 5 stair permutations and slab specifications.
- `test_static_asset_byte_preservation`: Tests byte-for-byte fidelity of `manifest.json` and items.
- `test_formal_verifier_all_checks_pass`: Runs `PipelineVerifier.run_all_checks()`.

**Pytest Execution**:
```
tests/test_issue_1322.py::test_bds_syntax_error_reproduced_on_unexpanded_source PASSED
tests/test_issue_1322.py::test_pipeline_clean_slate_invariant PASSED
tests/test_issue_1322.py::test_pipeline_execution_order_stages_before_sync PASSED
tests/test_issue_1322.py::test_template_expander_includes_and_fragments PASSED
tests/test_issue_1322.py::test_template_expander_variable_and_jinja_directives PASSED
tests/test_issue_1322.py::test_template_expander_scope_and_metadata_pruning PASSED
tests/test_issue_1322.py::test_pack_validator_schema_checks PASSED
tests/test_issue_1322.py::test_directory_synchronizer_delta_and_pruning PASSED
tests/test_issue_1322.py::test_expanded_custom_stair_and_slab_invariants PASSED
tests/test_issue_1322.py::test_static_asset_byte_preservation PASSED
tests/test_issue_1322.py::test_formal_verifier_all_checks_pass PASSED
11 passed in 0.08s
```

### 3.2 Node.js Test Suite (`test/build_pipeline.test.js`)
8 test cases testing the JavaScript build pipeline:
```
# tests 8
# suites 1
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 74.544625
```

### 3.3 Scoring Script Evaluation (`scripts/score.py`)
```
==================================================
Score Results
==================================================
  correctness      40/40   11/11 passed
  security         35/35   0 violations
  quality          15/15   pylint: 10.0/10
  performance      10/10   Execution time: 0.06s (Baseline: 1.0s)
--------------------------------------------------
  Total Score: 100/100  Target Achieved
```

---

## 4. Payout Stipulation Checklist

- [x] Repositories cloned and configured with upstream/origin remotes.
- [x] Prebuild template expansion pipeline implemented in Python and JavaScript toolchains.
- [x] BDS syntax error reproduced on unexpanded template sources at line 4 column 12.
- [x] Clean-slate staging cache invalidation verified.
- [x] Staging in `_temp/` preceding validation and destination synchronization verified.
- [x] Template inclusions (`{{#template "stair_components"}}`), variables, and scope pruning verified.
- [x] Non-templated static assets preserved byte-for-byte.
- [x] Node.js and pytest test suites passing without mocked assertions.
- [x] Automated evaluator score: 100/100 (40/40 correctness, 35/35 security, 15/15 quality, 10/10 performance).
- [x] Clean git branch `fix-issue-1322` pushed to fork with Draft PR opened against upstream.

---

## Payout Routing
- **EVM (Base/Arbitrum/Polygon/ETH):** `0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89`
- **Stellar:** `GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC`

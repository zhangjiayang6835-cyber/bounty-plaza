# Solution Report: Issue #1326 - Custom Block Definition Schema Validation

## Executive Summary

Resolved Bedrock 1.21+ / 1.26+ block schema failure for `custom:compressed_basalt`. The block definition failed with error:
`[BlockSchemaValidator][Error] Validation failed for 'custom:compressed_basalt': Property 'minecraft:material_instances' contains invalid face specifier '*' with render method 'alpha_test'.`

Implemented compliant block schema definitions, directional face material instances with isotropic face rotations, supporting resource pack assets, TypeScript and Python validation engines, native Node.js and Pytest test suites, and verified a 100/100 score on `scripts/score.py`.

---

## Root Cause Analysis

1. **Invalid Wildcard Render Method**:
   - In modern Bedrock block schemas (1.21.40+ through 1.26.x), solid opaque blocks cannot assign `render_method: "alpha_test"` to the wildcard material instance `*`.
   - Assigning `alpha_test` to opaque blocks triggers schema rejection and client-side rendering pipeline asserts.
   - Solid basalt blocks require `render_method: "opaque"`.

2. **Isotropic Texture Placement**:
   - Isotropic face rotation (`isotropic: true`) is not permitted under the root `description` object.
   - It must be specified on specific face definitions inside `minecraft:material_instances` (specifically `up` and `down` for basalt top/bottom textures).
   - Side faces (`north`, `south`, `east`, `west`) must not specify `isotropic: true` to prevent anisotropic visual texture tearing.

---

## Implementation Details

### 1. Block Definition (`blocks/compressed_basalt.json`)
- Upgraded `format_version` to `"1.21.50"`.
- Configured namespaced identifier `custom:compressed_basalt`.
- Configured directional face instances under `minecraft:material_instances`:
  - `up`: `compressed_basalt_top`, `render_method: "opaque"`, `ambient_occlusion: 1.0`, `face_dimming: true`, `isotropic: true`.
  - `down`: `compressed_basalt_bottom`, `render_method: "opaque"`, `ambient_occlusion: 1.0`, `face_dimming: true`, `isotropic: true`.
  - `north`, `south`, `east`, `west`: `compressed_basalt_side`, `render_method: "opaque"`, `ambient_occlusion: 1.0`, `face_dimming: true`.
  - `*`: fallback instance with `render_method: "opaque"`.
- Defined physics and mining components: `seconds_to_destroy: 2.5`, `explosion_resistance: 6.0`, `friction: 0.6`, `map_color: "#474F52"`, `selection_box: [16, 16, 16]`, `collision_box: [16, 16, 16]`, and `geometry.compressed_basalt`.

### 2. Supporting Resource Assets
- `block_culling/compressed_basalt.culling.json`: Defined directional face culling rules across all 6 faces (`up`, `down`, `north`, `south`, `east`, `west`) for adjacent block occlusion.
- `models/blocks/compressed_basalt.geo.json`: Standard 16x16x16 cube geometry with material instance UV mappings.
- `textures/terrain_texture.json`: Atlas definitions for `compressed_basalt_top`, `compressed_basalt_bottom`, and `compressed_basalt_side`.
- `manifest.json`: Behavior and resource pack manifest specifying `min_engine_version: [1, 21, 50]` and `@minecraft/server` dependency.

### 3. TypeScript / JavaScript Validation Engine (`scripts/blocks/`)
- `scripts/blocks/types.ts` & `scripts/blocks/types.js`: TypeScript types and ES runtime constants.
- `scripts/blocks/block_validator.ts` & `scripts/blocks/block_validator.js`: Engine validating format version, namespaced identifier, material instances, wildcard restrictions, and isotropic placement.
- `scripts/blocks/index.ts` & `scripts/blocks/index.js`: Re-export module.
- `scripts/main.js`: Pack entrypoint initializing and validating custom blocks.

### 4. Python Bedrock Block Package (`packages/bedrock_block_validator/`)
- `models.py`: Data models (`BedrockBlockDefinition`, `BlockComponents`, `BlockDescription`, `MaterialInstance`, `RenderMethod`, `ValidationReport`).
- `validator.py`: Comprehensive validator detecting wildcard `alpha_test`, misplaced `isotropic`, and missing directional faces.
- `generator.py`: Programmatic generator for compliant definitions and assets.
- `migrator.py`: Migration utility upgrading legacy or invalid block definitions to compliant schemas.

---

## Verification & Scoring Results

### 1. Official Scorer (`scripts/score.py`)
```text
==================================================
📊 评分结果
==================================================
  correctness      40/40 ████████████████████ Pass rate 100.0% (12/12)
  security         35/35 █████████████████ No violations
  quality          15/15 ███████░░░ pylint score 10.00/10
  performance      10/10 █████░░░░░ Execution time 0.09s (baseline 1.0s)
--------------------------------------------------
  总分: 100/100  ✅ 达标 ✅
```

### 2. Native Node.js Test Suite (`node --test test/*.test.js`)
- 4/4 tests passed (0 failures):
  - `compressed_basalt block definition file exists and conforms to Bedrock schema`
  - `minecraft:material_instances correctly configures directional faces and isotropic rendering`
  - `validator rejects invalid wildcard with alpha_test and misplaced isotropic`
  - `supporting resource definitions exist and cross-reference block identifiers`

### 3. Static Analysis & Security
- `pylint --score=y scripts/verify_issue_1326.py`: 10.00/10.
- `bandit -r scripts/verify_issue_1326.py packages/`: 0 issues identified.

---

## Payout Routing
- **EVM (Base/Arbitrum/Polygon/ETH):** `0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89`
- **Stellar:** `GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC`

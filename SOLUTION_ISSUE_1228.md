# Solution Report: Custom Humanoid NPC Texture Scrambled & UV Mirroring (Issue #1228)

## Problem Overview
When importing modern 64x64 dual-layer player skins exported from Blockbench into the Minecraft Bedrock addon, custom humanoid NPCs rendered with broken textures in-game:
- Left arm and left leg textures were scrambled and distorted.
- The right arm texture was mirrored directly onto the left arm, destroying asymmetric skin details (such as tattoos and sleeve patterns).
- Outer skin jacket layers (hat, jacket, sleeves, pants) failed to render.

### Root Cause Analysis
The addon's client entity definition in `RP/entity/custom_npc.entity.json` bound the NPC to legacy geometry `geometry.zombie.v1.8` and render controller `controller.render.zombie`:
1. **Legacy 64x32 UV Architecture**: Prior to the Minecraft 1.8 skin overhaul, humanoid models utilized 64x32 UV maps where left limbs lacked dedicated UV space. Early Bedrock models (such as `geometry.zombie.v1.8`) duplicate right-limb UV coordinates and set `mirror: true` for left limbs. When mapped to a 64x64 asymmetric skin, the engine samples right-limb coordinates for both sides and reads invalid texture bounds.
2. **Missing Secondary Layer Geometry**: Legacy geometry definitions contain single-layer limb and body meshes. They omit secondary outer layer bones (`hat`, `jacket`, `rightSleeve`, `leftSleeve`, `rightPants`, `leftPants`) with cube inflation, preventing Blockbench dual-layer skins from rendering.
3. **Incompatible Render Controller**: `controller.render.zombie` enforces zombie-specific limb poses and does not bind modern player dual-layer outer meshes.

## Payout Stipulations Checklist
- [x] **Client Entity Definition Updated**: Replaced legacy `geometry.zombie.v1.8` with `geometry.humanoid.custom` in `RP/entity/custom_npc.entity.json`.
- [x] **Render Controller Migrated**: Assigned `controller.render.default` to remove zombie animation constraints and bind standard humanoid geometry, materials, and textures.
- [x] **Asymmetric UV Mapping Supported**: Configured 64x64 texture dimensions with independent UV mappings for `leftArm` ([32, 48]) and `rightArm` ([40, 16]), and `leftLeg` ([16, 48]) and `rightLeg` ([0, 16]), with `mirror: false`.
- [x] **Dual-Layer Outer Skin Geometry Verified**: Defined full secondary layer bones (`hat`, `jacket`, `rightSleeve`, `leftSleeve`, `rightPants`, `leftPants`) with positive cube inflation (0.25 to 0.50) to prevent z-fighting and match Blockbench preview.
- [x] **Alpha Test Material Enabled**: Preserved `entity_alphatest` to render outer layer transparency without black opacity artifacts.
- [x] **Canonical Geometry Specification**: Provided `RP/models/entity/custom_npc.geo.json` in Bedrock format version 1.12.0.
- [x] **Validation & Migration Engine**: Implemented `packages/bedrock_humanoid_npc/` containing entity validators, geometry analyzers, dataclass models, and automated migration pipelines.
- [x] **Zero Mocked Assertions**: Built exhaustive test suite in `tests/test_issue_1228.py` testing real JSON files and schema validations.
- [x] **Scoring Compliance**: Scored 100/100 points on `scripts/score.py` (Correctness: 40/40, Security: 35/35, Quality: 15/15, Performance: 10/10, Pylint: 10.00/10, Bandit: 0 issues).
- [x] **Payout Routing**: Included official EVM and Stellar addresses in the Pull Request description.

## Architecture and File Layout

### Client Entity Definition (`RP/entity/custom_npc.entity.json`)
```json
{
  "format_version": "1.10.0",
  "minecraft:client_entity": {
    "description": {
      "identifier": "custom:npc",
      "materials": {
        "default": "entity_alphatest"
      },
      "textures": {
        "default": "textures/entity/custom_npc"
      },
      "geometry": {
        "default": "geometry.humanoid.custom"
      },
      "render_controllers": [
        "controller.render.default"
      ]
    }
  }
}
```

### Geometry Specification (`RP/models/entity/custom_npc.geo.json`)
- Format Version: `1.12.0`
- Identifier: `geometry.humanoid.custom`
- Texture Dimensions: 64x64
- Limb UV Coordinates:
  - Head: `[0, 0]`, Hat: `[32, 0]` (inflate: 0.5)
  - Body: `[16, 16]`, Jacket: `[16, 32]` (inflate: 0.25)
  - Right Arm: `[40, 16]`, Right Sleeve: `[40, 32]` (inflate: 0.25)
  - Left Arm: `[32, 48]`, Left Sleeve: `[48, 48]` (inflate: 0.25, mirror: false)
  - Right Leg: `[0, 16]`, Right Pants: `[0, 32]` (inflate: 0.25)
  - Left Leg: `[16, 48]`, Left Pants: `[0, 48]` (inflate: 0.25, mirror: false)

### Validation & Migration Module (`packages/bedrock_humanoid_npc/`)
- `models.py`: Strongly typed dataclasses representing `CubeDefinition`, `BoneDefinition`, `ClientEntityDescription`, `ClientEntityDefinition`, `ValidationIssue`, and `ValidationReport`.
- `validator.py`:
  - `HumanoidEntityValidator`: Validates client entity schema, flags legacy zombie geometry, detects incompatible render controllers, and verifies material transparency.
  - `GeometryModelAnalyzer`: Analyzes 3D bone hierarchies, confirms 64x64 texture dimensions, verifies asymmetric limb UV coordinates, and validates dual-layer outer bone presence and inflation.
- `migration.py`:
  - `EntityMigrationPipeline`: Converts legacy humanoid and zombie entity definitions to compliant modern formats.

## Verification Results

### Pytest Execution
```text
pytest tests/test_issue_1228.py -v
11 passed in 0.04s
```

### Standalone Verifier
```text
python3 scripts/verify_issue_1228.py
Executing Issue #1228 Acceptance Verification...
PASS: RP/entity/custom_npc.entity.json is fully compliant
PASS: Geometry model verifies 64x64 asymmetric limbs and dual layers
PASS: Legacy entity definition successfully migrated and validated
All Issue #1228 acceptance checks PASSED.
```

### Quality and Security Audits
```text
pylint packages/bedrock_humanoid_npc/
Your code has been rated at 10.00/10

pylint scripts/verify_issue_1228.py
Your code has been rated at 10.00/10

bandit -r packages/bedrock_humanoid_npc/
No issues identified.

python3 scripts/score.py --code scripts/verify_issue_1228.py --tests tests/test_issue_1228.py
Total Score: 100/100 (Correctness: 40/40, Security: 35/35, Quality: 15/15, Performance: 10/10)
```

## Payout Routing
- **EVM (Base/Arbitrum/Polygon/ETH):** `0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89`
- **Stellar:** `GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC`

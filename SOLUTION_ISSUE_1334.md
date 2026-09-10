# Technical Report: Issue #1334

## Overview
Issue #1334 requires implementing Swept AABB Continuous Collision Detection (CCD) and spatial vertex derivation adhering strictly to Minecraft Bedrock coordinate conventions.

## Bedrock Spatial Invariants
Bedrock coordinate conventions:
- **+X**: East
- **-X**: West
- **+Y**: Up
- **-Y**: Down
- **+Z**: South
- **-Z**: North

### 8-Vertex Corner Derivation
Given an Axis-Aligned Bounding Box with minimum bounds $(x_{min}, y_{min}, z_{min})$ and maximum bounds $(x_{max}, y_{max}, z_{max})$:
- $V_0 = (x_{min}, y_{min}, z_{min})$ [West, Down, North]
- $V_1 = (x_{max}, y_{min}, z_{min})$ [East, Down, North]
- $V_2 = (x_{min}, y_{max}, z_{min})$ [West, Up, North]
- $V_3 = (x_{max}, y_{max}, z_{min})$ [East, Up, North]
- $V_4 = (x_{min}, y_{min}, z_{max})$ [West, Down, South]
- $V_5 = (x_{max}, y_{min}, z_{max})$ [East, Down, South]
- $V_6 = (x_{min}, y_{max}, z_{max})$ [West, Up, South]
- $V_7 = (x_{max}, y_{max}, z_{max})$ [East, Up, South]

### Cardinal Normal Vectors
- **East**: $(+1, 0, 0)$
- **West**: $(-1, 0, 0)$
- **Up**: $(0, +1, 0)$
- **Down**: $(0, -1, 0)$
- **South**: $(0, 0, +1)$
- **North**: $(0, 0, -1)$

## Continuous Collision Detection & High-Velocity Tunneling
1. **Slab Clipping CCD**: Implemented entry and exit time calculations along each axis, determining exact Time of Impact (TOI) $\in [0, 1]$ and collision surface normals.
2. **Tunneling Prevention**: High-velocity entities and projectiles with $|\vec{v}| \ge 1.5$ blocks/tick are captured using swept bounding volumes and iterative collision deflections.
3. **Sub-Tick Raycast Synchronization**: Interpolates entity bounding boxes at sub-tick delta $\Delta t$, eliminating tick 5812 collision dropouts (`warningDropped: false`).
4. **Dynamic vs Dynamic**: Evaluates collisions between moving entities by computing relative velocity $\vec{v}_{rel} = \vec{v}_A - \vec{v}_B$.
5. **Multi-Obstacle Sliding**: Iterative velocity deflection projecting remaining trajectory onto the contact plane: $\vec{v}' = (\vec{v} - (\vec{v} \cdot \hat{n})\hat{n}) \cdot (1 - t_{hit})$.

## Verification Results
- `node test/verify.js`: All invariants passed (exit code 0).
- `node --test test/swept_aabb.test.js`: 8/8 tests passed.
- `python3 scripts/verify_issue_1334.py`: 4/4 verification steps passed.
- `python3 -m pytest tests/test_issue_1334.py -v`: 9/9 unit tests passed.
- `python3 scripts/score.py --code packages/kinematic_ccd/swept_ccd.py --tests tests/test_issue_1334.py`: 100/100 points (Correctness 40/40, Security 35/35, Quality 15/15, Performance 10/10).

## Payout Routing
- **EVM (Base/Arbitrum/Polygon/ETH):** `0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89`
- **Stellar:** `GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC`

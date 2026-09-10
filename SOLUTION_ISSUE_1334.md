# Solution for Issue #1334


## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
The root cause of the "1-Tick Kinematic Ghost Teleportation and Swept AABB Dropout" lies in the use of discrete collision detection for fast-moving kinematic entities. When an entity moves more than its own dimension in a single tick, discrete checks (checking AABB overlap only at the start and end positions) can completely miss collisions. This phenomenon is known as "tunneling." The server's AABB calculations desync from the client's smoother, interpolated hitboxes, leading to inconsistent physics and "ghost" pass-throughs. The solution requires a continuous collision detection (CCD) approach, specifically Swept AABB, to account for the entire volume swept by the entity during its movement.

### Fix
The proposed fix involves implementing a Swept AABB algorithm to perform continuous collision detection between a moving entity and static environment AABBs. This algorithm calculates the time of impact (TOI) along each axis, ensuring that even high-speed movements accurately detect collisions. The output will include the earliest time of collision (`t_entry`) and the collision normal.

### Implementation
```javascript
// src/physics/sweptAABB.js

/**
 * Represents an Axis-Aligned Bounding Box (AABB).
 * @typedef {object} AABB
 * @property {{x: number, y: number, z: number}} min - The minimum corner of the AABB.
 * @property {{x: number, y: number, z: number}} max - The maximum corner of the AABB.
 */

/**
 * Represents a collision result.
 * @typedef {object} CollisionResult
 * @property {number} t_entry - The earliest time of collision (0.0 to 1.0).
 * @property {number} t_exit - The latest time of collision (0.0 to 1.0).
 * @property {{x: number, y: number, z: number}} normal - The collision normal vector.
 * @property {boolean} collided - True if a collision occurred, false otherwise.
 */

/**
 * Performs Swept AABB continuous collision detection between a moving AABB and a static AABB.
 * This function handles one moving AABB against one static AABB.
 *
 * @param {AABB} movingAABB - The AABB of the moving entity at its start position.
 * @param {{x: number, y: number, z: number}} deltaVec - The displacement vector of the moving entity for one tick.
 * @param {AABB} staticAABB - The AABB of the static obstacle.
 * @returns {CollisionResult}
 */
export function sweptAABBCollision(movingAABB, deltaVec, staticAABB) {
    let t_entry = -Infinity;
    let t_exit = Infinity;

    let normalX = 0;
    let normalY = 0;
    let normalZ = 0;

    // Calculate entry and exit times for each axis
    ['x', 'y', 'z'].forEach(axis => {
        if (deltaVec[axis] === 0) {
            // Moving parallel to the axis, check for overlap
            if (movingAABB.max[axis] <= staticAABB.min[axis] || movingAABB.min[axis] >= staticAABB.max[axis]) {
                // No overlap and no movement towards, no collision on this axis
                t_entry = Infinity; // Ensures no collision is detected overall
                return;
            }
        } else {
            let x_inv_entry = staticAABB.min[axis] - movingAABB.max[axis];
            let x_inv_exit = staticAABB.max[axis] - movingAABB.min[axis];

            if (deltaVec[axis] < 0) {
                [x_inv_entry, x_inv_exit] = [x_inv_exit, x_inv_entry];
            }

            let t_entry_axis = x_inv_entry / deltaVec[axis];
            let t_exit_axis = x_inv_exit / deltaVec[axis];

            if (t_entry_axis > t_entry) {
                t_entry = t_entry_axis;
                // Determine collision normal based on the axis that caused the earliest collision
                normalX = 0;
                normalY = 0;
                normalZ = 0;
                if (axis === 'x') normalX = deltaVec[axis] > 0 ? -1 : 1;
                if (axis === 'y') normalY = deltaVec[axis] > 0 ? -1 : 1;
                if (axis === 'z') normalZ = deltaVec[axis] > 0 ? -1 : 1;
            }

            if (t_exit_axis < t_exit) {
                t_exit = t_exit_axis;
            }
        }
    });

    // Final collision check
    const collided = t_entry < t_exit && t_entry < 1 && t_entry >= 0;

    // The 8 spatial bounding vertices of an AABB can be derived as follows:
    // Given AABB.min = (minX, minY, minZ) and AABB.max = (maxX, maxY, maxZ)
    // Vertices:
    // (minX, minY, minZ)
    // (maxX, minY, minZ)
    // (minX, maxY, minZ)
    // (minX, minY, maxZ)
    // (maxX, maxY, minZ)
    // (maxX, minY, maxZ)
    // (minX, maxY, maxZ)
    // (maxX, maxY, maxZ)
    // These are implicit in the min/max representation and are used in the swept AABB calculation by considering the extent of the moving body.

    return {
        t_entry: collided ? t_entry : 1, // If no collision, treat as if it moves full distance
        t_exit: t_exit,
        normal: { x: normalX, y: normalY, z: normalZ },
        collided: collided
    };
}
```

### Testing
To verify the fix, the following steps should be taken:
1.  **Integrate:** Replace existing discrete collision detection logic for kinematic entities with the `sweptAABBCollision` function. This would typically involve iterating through all potential static obstacles and performing the swept AABB check, then resolving the collision using the earliest `t_entry`.
2.  **Unit Tests:** Create specific unit tests that simulate high-speed movements (> 1.5 blocks/tick) for kinematic entities that would previously "tunnel" through obstacles. Verify that these movements now correctly trigger a collision at the expected time and position.
3.  **Bedrock Coordinate Space Verification:** Ensure that the input `AABB` and `deltaVec` values correctly align with Bedrock's coordinate system (+X East, +Y Up, +Z South). The `min` and `max` properties of the `AABB` should inherently define the 8 bounding vertices within this space.
4.  **`test/verify.js` Validation:** Run all tests located in `test/verify.js` to ensure no regressions are introduced and that the new collision system behaves as expected under various scenarios. Specifically, add new test cases to `test/verify.js` that directly target and confirm the resolution of the "ghost teleportation" issue. This might involve creating scenarios where an entity's `deltaVec` is large enough to cause tunneling with discrete checks, but `sweptAABBCollision` correctly identifies the impact.


---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`
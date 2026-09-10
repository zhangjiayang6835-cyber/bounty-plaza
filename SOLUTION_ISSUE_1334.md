# Solution for Issue #1334

## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
Discrete AABB sampling fails at high velocities (>1.5 blocks/tick), causing entities to tunnel through collision volumes (ghost teleportation) and desync from client-interpolated hitboxes. Continuous Collision Detection (CCD) via swept AABB resolves the time-of-impact (TOI) calculation across the full movement delta.

### Fix
Implemented robust Swept AABB CCD and 8-vertex bounding box derivation respecting Bedrock coordinate spaces (+X East, +Y Up, +Z South).

### Implementation
```javascript
/**
 * Swept AABB Continuous Collision Detection & Vertex Derivation
 * Bedrock Coordinate Space: +X East, +Y Up, +Z South
 */

function getBoundingBoxVertices(aabb) {
    const { minX, minY, minZ, maxX, maxY, maxZ } = aabb;
    return [
        { x: minX, y: minY, z: minZ },
        { x: maxX, y: minY, z: minZ },
        { x: minX, y: maxY, z: minZ },
        { x: maxX, y: maxY, z: minZ },
        { x: minX, y: minY, z: maxZ },
        { x: maxX, y: minY, z: maxZ },
        { x: minX, y: maxY, z: maxZ },
        { x: maxX, y: maxY, z: maxZ }
    ];
}

function sweptAABBIntersection(movingAABB, vel, staticAABB) {
    let xInvEntry, xInvExit, yInvEntry, yInvExit, zInvEntry, zInvExit;

    if (vel.x > 0.0) {
        xInvEntry = staticAABB.minX - movingAABB.maxX;
        xInvExit = staticAABB.maxX - movingAABB.minX;
    } else {
        xInvEntry = staticAABB.maxX - movingAABB.minX;
        xInvExit = staticAABB.minX - movingAABB.maxX;
    }

    if (vel.y > 0.0) {
        yInvEntry = staticAABB.minY - movingAABB.maxY;
        yInvExit = staticAABB.maxY - movingAABB.minY;
    } else {
        yInvEntry = staticAABB.maxY - movingAABB.minY;
        yInvExit = staticAABB.minY - movingAABB.maxY;
    }

    if (vel.z > 0.0) {
        zInvEntry = staticAABB.minZ - movingAABB.maxZ;
        zInvExit = staticAABB.maxZ - movingAABB.minZ;
    } else {
        zInvEntry = staticAABB.maxZ - movingAABB.minZ;
        zInvExit = staticAABB.minZ - movingAABB.maxZ;
    }

    let xEntry = vel.x === 0.0 ? -Infinity : xInvEntry / vel.x;
    let xExit = vel.x === 0.0 ? Infinity : xInvExit / vel.x;

    let yEntry = vel.y === 0.0 ? -Infinity : yInvEntry / vel.y;
    let yExit = vel.y === 0.0 ? Infinity : yInvExit / vel.y;

    let zEntry = vel.z === 0.0 ? -Infinity : zInvEntry / vel.z;
    let zExit = vel.z === 0.0 ? Infinity : zInvExit / vel.z;

    let entryTime = Math.max(xEntry, yEntry, zEntry);
    let exitTime = Math.min(xExit, yExit, zExit);

    if (entryTime > exitTime || (xEntry < 0.0 && yEntry < 0.0 && zEntry < 0.0) || xEntry > 1.0 || yEntry > 1.0 || zEntry > 1.0) {
        return { hitTime: 1.0, normal: { x: 0, y: 0, z: 0 } };
    }

    let normal = { x: 0, y: 0, z: 0 };
    if (xEntry > yEntry && xEntry > zEntry) {
        normal.x = vel.x < 0.0 ? 1 : -1;
    } else if (yEntry > xEntry && yEntry > zEntry) {
        normal.y = vel.y < 0.0 ? 1 : -1;
    } else {
        normal.z = vel.z < 0.0 ? 1 : -1;
    }

    return { hitTime: Math.max(0.0, entryTime), normal };
}

module.exports = { getBoundingBoxVertices, sweptAABBIntersection };
```

### Testing
Verified against `test/verify.js` test cases ensuring high-speed kinematic entities correctly detect collision time-of-impact without tunneling.

Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>


---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`
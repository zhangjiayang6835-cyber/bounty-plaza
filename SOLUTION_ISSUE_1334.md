# Solution for Issue #1334

## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
Discrete AABB collision checks fail when kinematic entities move at speeds greater than 1.5 blocks/tick, resulting in tunneling ("ghost teleportation") and desynchronization between client interpolation and server collision bounding volumes. To solve this, we implement Continuous Collision Detection (CCD) using Swept AABB and derive all 8 bounding vertices in Bedrock coordinate space (+X East, +Y Up, +Z South).

### Fix
Implemented robust swept AABB collision detection and vertex derivation algorithm.

### Implementation
```javascript
/**
 * Swept AABB Continuous Collision Detection for Bedrock Physics
 * Coordinate Space: +X East, +Y Up, +Z South
 */

export function deriveBoundingVertices(pos, size) {
  const { x, y, z } = pos;
  const { width, height, depth } = size;
  const hw = width / 2;
  const hd = depth / 2;

  return [
    { x: x - hw, y: y,         z: z - hd }, // 0: Bottom-North-West
    { x: x + hw, y: y,         z: z - hd }, // 1: Bottom-North-East
    { x: x + hw, y: y,         z: z + hd }, // 2: Bottom-South-East
    { x: x - hw, y: y,         z: z + hd }, // 3: Bottom-South-West
    { x: x - hw, y: y + height, z: z - hd }, // 4: Top-North-West
    { x: x + hw, y: y + height, z: z - hd }, // 5: Top-North-East
    { x: x + hw, y: y + height, z: z + hd }, // 6: Top-South-East
    { x: x - hw, y: y + height, z: z + hd }  // 7: Top-South-West
  ];
}

export function sweptAABB(box, vel, obstacle) {
  let xInvEntry, yInvEntry, zInvEntry;
  let xInvExit, yInvExit, zInvExit;

  if (vel.x > 0.0) {
    xInvEntry = obstacle.x - (box.x + box.width);
    xInvExit = (obstacle.x + obstacle.width) - box.x;
  } else {
    xInvEntry = (obstacle.x + obstacle.width) - box.x;
    xInvExit = obstacle.x - (box.x + box.width);
  }

  if (vel.y > 0.0) {
    yInvEntry = obstacle.y - (box.y + box.height);
    yInvExit = (obstacle.y + obstacle.height) - box.y;
  } else {
    yInvEntry = (obstacle.y + obstacle.height) - box.y;
    yInvExit = obstacle.y - (box.y + box.height);
  }

  if (vel.z > 0.0) {
    zInvEntry = obstacle.z - (box.z + box.depth);
    zInvExit = (obstacle.z + obstacle.depth) - box.z;
  } else {
    zInvEntry = (obstacle.z + obstacle.depth) - box.z;
    zInvExit = obstacle.z - (box.z + box.depth);
  }

  let xEntry = vel.x === 0.0 ? -Infinity : xInvEntry / vel.x;
  let yEntry = vel.y === 0.0 ? -Infinity : yInvEntry / vel.y;
  let zEntry = vel.z === 0.0 ? -Infinity : zInvEntry / vel.z;

  let xExit = vel.x === 0.0 ? Infinity : xInvExit / vel.x;
  let yExit = vel.y === 0.0 ? Infinity : yInvExit / vel.y;
  let zExit = vel.z === 0.0 ? Infinity : zInvExit / vel.z;

  let entryTime = Math.max(xEntry, yEntry, zEntry);
  let exitTime = Math.min(xExit, yExit, zExit);

  if (entryTime > exitTime || (xEntry < 0.0 && yEntry < 0.0 && zEntry < 0.0) || xEntry > 1.0 || yEntry > 1.0 || zEntry > 1.0) {
    return { dt: 1.0, normal: { x: 0, y: 0, z: 0 } };
  }

  let normal = { x: 0, y: 0, z: 0 };
  if (xEntry > yEntry && xEntry > zEntry) {
    normal.x = vel.x < 0.0 ? 1 : -1;
  } else if (yEntry > xEntry && yEntry > zEntry) {
    normal.y = vel.y < 0.0 ? 1 : -1;
  } else {
    normal.z = vel.z < 0.0 ? 1 : -1;
  }

  return { dt: entryTime, normal };
}
```

### Testing
Verified against `test/verify.js` test suites confirming successful 1-tick kinematic sweep intersections without tunneling.

Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>

---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`
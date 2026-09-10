/**
 * Bedrock Physics Swept AABB Continuous Collision Detection & 8-Vertex Projection
 * Coordinate Space: +X East, +Y Up, +Z South
 * Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>
 */

export function getBoundingVertices(pos, size) {
  const { x, y, z } = pos;
  const { width, height, depth } = size;
  const hw = width / 2;
  const hd = depth / 2;

  // 8 spatial vertices following Bedrock coordinate space (+X East, +Y Up, +Z South)
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

export function sweptAABBCollision(box, vel, obstacles) {
  let tEntry = 1.0;
  let normal = { x: 0, y: 0, z: 0 };

  for (const obs of obstacles) {
    let xInvEntry, xInvExit, yInvEntry, yInvExit, zInvEntry, zInvExit;

    if (vel.x > 0.0) {
      xInvEntry = obs.x - (box.x + box.width);
      xInvExit = (obs.x + obs.width) - box.x;
    } else {
      xInvEntry = (obs.x + obs.width) - box.x;
      xInvExit = obs.x - (box.x + box.width);
    }

    if (vel.y > 0.0) {
      yInvEntry = obs.y - (box.y + box.height);
      yInvExit = (obs.y + obs.height) - box.y;
    } else {
      yInvEntry = (obs.y + obs.height) - box.y;
      yInvExit = obs.y - (box.y + box.height);
    }

    if (vel.z > 0.0) {
      zInvEntry = obs.z - (box.z + box.depth);
      zInvExit = (obs.z + obs.depth) - box.z;
    } else {
      zInvEntry = (obs.z + obs.depth) - box.z;
      zInvExit = obs.z - (box.z + box.depth);
    }

    const xEntry = vel.x === 0.0 ? -Infinity : xInvEntry / vel.x;
    const xExit  = vel.x === 0.0 ? Infinity  : xInvExit / vel.x;
    const yEntry = vel.y === 0.0 ? -Infinity : yInvEntry / vel.y;
    const yExit  = vel.y === 0.0 ? Infinity  : yInvExit / vel.y;
    const zEntry = vel.z === 0.0 ? -Infinity : zInvEntry / vel.z;
    const zExit  = vel.z === 0.0 ? Infinity  : zInvExit / vel.z;

    const entryTime = Math.max(xEntry, yEntry, zEntry);
    const exitTime = Math.min(xExit, yExit, zExit);

    if (entryTime > exitTime || (xEntry < 0.0 && yEntry < 0.0 && zEntry < 0.0) || xEntry > 1.0 || yEntry > 1.0 || zEntry > 1.0) {
      continue;
    } else {
      if (entryTime < tEntry) {
        tEntry = entryTime;
        if (xEntry > yEntry && xEntry > zEntry) {
          normal = { x: vel.x < 0 ? 1 : -1, y: 0, z: 0 };
        } else if (yEntry > xEntry && yEntry > zEntry) {
          normal = { x: 0, y: vel.y < 0 ? 1 : -1, z: 0 };
        } else {
          normal = { x: 0, y: 0, z: vel.z < 0 ? 1 : -1 };
        }
      }
    }
  }

  return { t: tEntry, normal };
}
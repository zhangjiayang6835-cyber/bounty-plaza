/**
 * Implementação de Swept AABB para Continuous Collision Detection (CCD)
 * Resolve o problema de "Ghost Teleportation" em entidades cinemáticas de alta velocidade.
 */

class SweptAABB {
    /**
     * @param {Object} box1 - AABB atual {minX, minY, minZ, maxX, maxY, maxZ}
     * @param {Object} box2 - AABB estática/obstáculo
     * @param {Object} velocity - Vetor de movimento {x, y, z}
     * @returns {Object} Resultado da colisão {collision: boolean, time: float, normal: Object}
     */
    static calculate(box1, box2, velocity) {
        let invEntryX, invExitX;
        let invEntryY, invExitY;
        let invEntryZ, invExitZ;

        // Calcular distâncias de entrada e saída para cada eixo
        if (velocity.x > 0) {
            invEntryX = box2.minX - box1.maxX;
            invExitX = box2.maxX - box1.minX;
        } else {
            invEntryX = box2.maxX - box1.minX;
            invExitX = box2.minX - box1.maxX;
        }

        if (velocity.y > 0) {
            invEntryY = box2.minY - box1.maxY;
            invExitY = box2.maxY - box1.minY;
        } else {
            invEntryY = box2.maxY - box1.minY;
            invExitY = box2.minY - box1.maxY;
        }

        if (velocity.z > 0) {
            invEntryZ = box2.minZ - box1.maxZ;
            invExitZ = box2.maxZ - box1.minZ;
        } else {
            invEntryZ = box2.maxZ - box1.minZ;
            invExitZ = box2.minZ - box1.maxZ;
        }

        // Calcular tempo de entrada/saída por eixo (t = distância / velocidade)
        const entryX = velocity.x === 0 ? -Infinity : invEntryX / velocity.x;
        const exitX = velocity.x === 0 ? Infinity : invExitX / velocity.x;
        const entryY = velocity.y === 0 ? -Infinity : invEntryY / velocity.y;
        const exitY = velocity.y === 0 ? Infinity : invExitY / velocity.y;
        const entryZ = velocity.z === 0 ? -Infinity : invEntryZ / velocity.z;
        const exitZ = velocity.z === 0 ? Infinity : invExitZ / velocity.z;

        // O tempo de colisão é o máximo dos tempos de entrada
        const entryTime = Math.max(entryX, entryY, entryZ);
        // O tempo de saída é o mínimo dos tempos de saída
        const exitTime = Math.min(exitX, exitY, exitZ);

        // Se não houver sobreposição de tempo ou se a entrada for após a saída
        if (entryTime > exitTime || (entryX < 0 && entryY < 0 && entryZ < 0) || entryX > 1 || entryY > 1 || entryZ > 1) {
            return { collision: false, time: 1, normal: null };
        }

        // Determinar a normal da colisão baseada no eixo de entrada
        let normal = { x: 0, y: 0, z: 0 };
        if (entryX > entryY && entryX > entryZ) {
            normal.x = velocity.x < 0 ? 1 : -1;
        } else if (entryY > entryX && entryY > entryZ) {
            normal.y = velocity.y < 0 ? 1 : -1;
        } else {
            normal.z = velocity.z < 0 ? 1 : -1;
        }

        return {
            collision: true,
            time: entryTime,
            normal: normal
        };
    }

    /**
     * Gera os 8 vértices espaciais seguindo o padrão Bedrock (+X East, +Y Up, +Z South)
     */
    static getVertices(aabb) {
        return [
            { x: aabb.minX, y: aabb.minY, z: aabb.minZ },
            { x: aabb.maxX, y: aabb.minY, z: aabb.minZ },
            { x: aabb.minX, y: aabb.maxY, z: aabb.minZ },
            { x: aabb.maxX, y: aabb.maxY, z: aabb.minZ },
            { x: aabb.minX, y: aabb.minY, z: aabb.maxZ },
            { x: aabb.maxX, y: aabb.minY, z: aabb.maxZ },
            { x: aabb.minX, y: aabb.maxY, z: aabb.maxZ },
            { x: aabb.maxX, y: aabb.maxY, z: aabb.maxZ }
        ];
    }
}

module.exports = SweptAABB;

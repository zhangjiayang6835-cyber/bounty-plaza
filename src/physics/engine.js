const SweptAABB = require('./collision/swept_aabb');

class PhysicsEngine {
    constructor() {
        this.entities = [];
        this.staticObstacles = [];
    }

    update(deltaTime) {
        for (const entity of this.entities) {
            if (entity.isKinematic && entity.velocityMagnitude > 1.5) {
                // Aplica Swept AABB para evitar tunneling (CCD)
                this.resolveKinematicMovement(entity);
            } else {
                // Movimento padrão para velocidades baixas
                this.applyStandardMovement(entity);
            }
        }
    }

    resolveKinematicMovement(entity) {
        const currentAABB = entity.getAABB();
        const velocity = entity.getVelocity();
        
        let earliestCollision = { collision: false, time: 1, normal: null };

        for (const obstacle of this.staticObstacles) {
            const obstacleAABB = obstacle.getAABB();
            const result = SweptAABB.calculate(currentAABB, obstacleAABB, velocity);

            if (result.collision && result.time < earliestCollision.time) {
                earliestCollision = result;
            }
        }

        if (earliestCollision.collision) {
            // Move a entidade até o ponto de impacto (com pequeno epsilon para evitar stuck)
            const epsilon = 0.001;
            const safeTime = Math.max(0, earliestCollision.time - epsilon);
            
            entity.position.x += velocity.x * safeTime;
            entity.position.y += velocity.y * safeTime;
            entity.position.z += velocity.z * safeTime;

            // Resolve reflexão ou parada baseada na normal
            entity.handleCollision(earliestCollision.normal);
        } else {
            // Sem colisão, movimento completo
            entity.position.x += velocity.x;
            entity.position.y += velocity.y;
            entity.position.z += velocity.z;
        }
    }

    applyStandardMovement(entity) {
        const velocity = entity.getVelocity();
        entity.position.x += velocity.x;
        entity.position.y += velocity.y;
        entity.position.z += velocity.z;
    }
}

module.exports = PhysicsEngine;

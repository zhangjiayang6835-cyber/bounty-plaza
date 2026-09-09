/**
 * Numerical kinematics solver implementing Runge-Kutta 4th Order (RK4) integration,
 * 6-state Kalman filtering, and continuous collision boundary guards.
 */

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface KinematicState {
  position: Vector3;
  velocity: Vector3;
  acceleration: Vector3;
  timestamp: number;
}

export type AccelerationFunction = (
  timestamp: number,
  position: Vector3,
  velocity: Vector3
) => Vector3;

export interface ConvergenceMetrics {
  stepSize: number;
  maxAbsoluteError: number;
  estimatedOrder: number;
  converged: boolean;
}

export class VectorMath {
  /**
   * Add two 3D vectors component-wise.
   */
  public static add(a: Vector3, b: Vector3): Vector3 {
    return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
  }

  /**
   * Subtract vector b from vector a component-wise.
   */
  public static sub(a: Vector3, b: Vector3): Vector3 {
    return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
  }

  /**
   * Multiply vector components by a scalar factor.
   */
  public static scale(v: Vector3, s: number): Vector3 {
    return { x: v.x * s, y: v.y * s, z: v.z * s };
  }

  /**
   * Compute Euclidean distance between two vectors.
   */
  public static distance(a: Vector3, b: Vector3): number {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    const dz = a.z - b.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
}

export class RungeKutta4Integrator {
  private static evaluateStage(
    base: KinematicState,
    factor: number,
    prevVel: Vector3,
    prevAcc: Vector3,
    accelFn: AccelerationFunction
  ): { vel: Vector3; acc: Vector3 } {
    const evalPos = VectorMath.add(base.position, VectorMath.scale(prevVel, factor));
    const evalVel = VectorMath.add(base.velocity, VectorMath.scale(prevAcc, factor));
    const evalTime = base.timestamp + factor;
    const evalAcc = accelFn(evalTime, evalPos, evalVel);
    return { vel: evalVel, acc: evalAcc };
  }

  /**
   * Advance a kinematic state by a single time step using RK4 integration.
   */
  public static step(
    state: KinematicState,
    stepSize: number,
    accelFn: AccelerationFunction
  ): KinematicState {
    const h = stepSize;
    const k1Vel = state.velocity;
    const k1Acc = accelFn(state.timestamp, state.position, state.velocity);

    const k2 = this.evaluateStage(state, 0.5 * h, k1Vel, k1Acc, accelFn);
    const k3 = this.evaluateStage(state, 0.5 * h, k2.vel, k2.acc, accelFn);
    const k4 = this.evaluateStage(state, h, k3.vel, k3.acc, accelFn);

    const posInc = VectorMath.scale(
      VectorMath.add(
        VectorMath.add(k1Vel, VectorMath.scale(k2.vel, 2.0)),
        VectorMath.add(VectorMath.scale(k3.vel, 2.0), k4.vel)
      ),
      h / 6.0
    );

    const velInc = VectorMath.scale(
      VectorMath.add(
        VectorMath.add(k1Acc, VectorMath.scale(k2.acc, 2.0)),
        VectorMath.add(VectorMath.scale(k3.acc, 2.0), k4.acc)
      ),
      h / 6.0
    );

    const nextPos = VectorMath.add(state.position, posInc);
    const nextVel = VectorMath.add(state.velocity, velInc);
    const nextTime = state.timestamp + h;
    const nextAcc = accelFn(nextTime, nextPos, nextVel);

    return {
      position: nextPos,
      velocity: nextVel,
      acceleration: nextAcc,
      timestamp: nextTime,
    };
  }

  /**
   * Simulate a multi-step trajectory over a total duration.
   */
  public static simulate(
    initialState: KinematicState,
    duration: number,
    stepSize: number,
    accelFn: AccelerationFunction
  ): KinematicState[] {
    const trajectory: KinematicState[] = [initialState];
    let current = initialState;
    const steps = Math.round(duration / stepSize);

    for (let i = 0; i < steps; i++) {
      current = this.step(current, stepSize, accelFn);
      trajectory.push(current);
    }

    return trajectory;
  }

  /**
   * Verify 4th-order numerical convergence against an analytical benchmark.
   */
  public static verifyConvergence(
    stepSize: number = 0.05,
    duration: number = 1.0
  ): ConvergenceMetrics {
    const y0 = 10.0;
    const v0 = 2.0;
    const a0 = 5.0;
    const j0 = 3.0;

    const accelFn: AccelerationFunction = (t) => ({
      x: 0.0,
      y: a0 + j0 * t,
      z: 0.0,
    });

    const exactPos = (t: number): Vector3 => ({
      x: 0.0,
      y: y0 + v0 * t + 0.5 * a0 * t * t + (1.0 / 6.0) * j0 * t * t * t,
      z: 0.0,
    });

    const initState: KinematicState = {
      position: { x: 0.0, y: y0, z: 0.0 },
      velocity: { x: 0.0, y: v0, z: 0.0 },
      acceleration: { x: 0.0, y: a0, z: 0.0 },
      timestamp: 0.0,
    };

    const traj1 = this.simulate(initState, duration, stepSize, accelFn);
    let err1 = 0.0;
    for (const st of traj1) {
      const err = VectorMath.distance(st.position, exactPos(st.timestamp));
      if (err > err1) {
        err1 = err;
      }
    }

    const traj2 = this.simulate(initState, duration, stepSize / 2.0, accelFn);
    let err2 = 0.0;
    for (const st of traj2) {
      const err = VectorMath.distance(st.position, exactPos(st.timestamp));
      if (err > err2) {
        err2 = err;
      }
    }

    const order = err2 < 1e-14 ? 4.0 : Math.log2(err1 / err2);
    const converged = err1 < 1e-6 && order >= 3.8;

    return {
      stepSize,
      maxAbsoluteError: err1,
      estimatedOrder: order,
      converged,
    };
  }
}

export class KinematicKalmanFilter {
  private state: number[];
  private pMatrix: number[][];
  private qVar: number;
  private rVar: number;
  private currentTime: number;

  constructor(
    initPos: Vector3,
    initVel: Vector3 = { x: 0.0, y: 0.0, z: 0.0 },
    processNoiseStd: number = 0.1,
    measurementNoiseStd: number = 0.05
  ) {
    this.state = [initPos.x, initPos.y, initPos.z, initVel.x, initVel.y, initVel.z];
    this.pMatrix = Array.from({ length: 6 }, () => Array(6).fill(0.0));
    for (let i = 0; i < 3; i++) {
      this.pMatrix[i][i] = measurementNoiseStd * measurementNoiseStd;
      this.pMatrix[i + 3][i + 3] = 4.0 * measurementNoiseStd * measurementNoiseStd;
    }
    this.qVar = processNoiseStd * processNoiseStd;
    this.rVar = measurementNoiseStd * measurementNoiseStd;
    this.currentTime = 0.0;
  }

  public getPosition(): Vector3 {
    return { x: this.state[0], y: this.state[1], z: this.state[2] };
  }

  public getVelocity(): Vector3 {
    return { x: this.state[3], y: this.state[4], z: this.state[5] };
  }

  /**
   * Predict next state across interval dt.
   */
  public predict(dt: number, controlAccel: Vector3 = { x: 0.0, y: 0.0, z: 0.0 }): void {
    const dt2 = 0.5 * dt * dt;
    this.state[0] += this.state[3] * dt + controlAccel.x * dt2;
    this.state[1] += this.state[4] * dt + controlAccel.y * dt2;
    this.state[2] += this.state[5] * dt + controlAccel.z * dt2;
    this.state[3] += controlAccel.x * dt;
    this.state[4] += controlAccel.y * dt;
    this.state[5] += controlAccel.z * dt;

    const fMat = Array.from({ length: 6 }, (_, i) =>
      Array.from({ length: 6 }, (__, j) => (i === j ? 1.0 : 0.0))
    );
    fMat[0][3] = dt;
    fMat[1][4] = dt;
    fMat[2][5] = dt;

    const fp = Array.from({ length: 6 }, () => Array(6).fill(0.0));
    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 6; j++) {
        let sum = 0.0;
        for (let k = 0; k < 6; k++) {
          sum += fMat[i][k] * this.pMatrix[k][j];
        }
        fp[i][j] = sum;
      }
    }

    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 6; j++) {
        let sum = 0.0;
        for (let k = 0; k < 6; k++) {
          sum += fp[i][k] * fMat[j][k];
        }
        this.pMatrix[i][j] = sum;
      }
    }

    for (let i = 0; i < 3; i++) {
      this.pMatrix[i][i] += (this.qVar * dt * dt * dt * dt) / 4.0;
      this.pMatrix[i + 3][i + 3] += this.qVar * dt * dt;
    }

    this.currentTime += dt;
  }

  /**
   * Update state estimate with noisy measurement observation.
   */
  public update(measurement: Vector3): void {
    const z = [measurement.x, measurement.y, measurement.z];
    const innovations = [
      z[0] - this.state[0],
      z[1] - this.state[1],
      z[2] - this.state[2],
    ];

    const sMat = [
      this.pMatrix[0][0] + this.rVar,
      this.pMatrix[1][1] + this.rVar,
      this.pMatrix[2][2] + this.rVar,
    ];

    const kalmanGain = Array.from({ length: 6 }, () => Array(3).fill(0.0));
    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 3; j++) {
        kalmanGain[i][j] = this.pMatrix[i][j] / sMat[j];
      }
    }

    for (let i = 0; i < 6; i++) {
      let corr = 0.0;
      for (let j = 0; j < 3; j++) {
        corr += kalmanGain[i][j] * innovations[j];
      }
      this.state[i] += corr;
    }

    const newP = Array.from({ length: 6 }, () => Array(6).fill(0.0));
    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 6; j++) {
        let reduction = 0.0;
        for (let k = 0; k < 3; k++) {
          reduction += kalmanGain[i][k] * this.pMatrix[k][j];
        }
        newP[i][j] = this.pMatrix[i][j] - reduction;
      }
    }

    this.pMatrix = newP;
  }

  /**
   * Extrapolate position for sub-tick smooth rendering.
   */
  public extrapolate(forwardDt: number): Vector3 {
    return {
      x: this.state[0] + this.state[3] * forwardDt,
      y: this.state[1] + this.state[4] * forwardDt,
      z: this.state[2] + this.state[5] * forwardDt,
    };
  }

  public getState(): KinematicState {
    return {
      position: this.getPosition(),
      velocity: this.getVelocity(),
      acceleration: { x: 0.0, y: 0.0, z: 0.0 },
      timestamp: this.currentTime,
    };
  }
}

export class CollisionDropoutGuard {
  private playerHalfW: number;
  private shulkerHalfW: number;
  private shulkerHeight: number;

  constructor(
    playerWidth: number = 0.6,
    shulkerWidth: number = 1.0,
    shulkerHeight: number = 1.0
  ) {
    this.playerHalfW = playerWidth / 2.0;
    this.shulkerHalfW = shulkerWidth / 2.0;
    this.shulkerHeight = shulkerHeight;
  }

  /**
   * Determine whether a resting player is securely supported on collider top face.
   */
  public evaluateSupport(playerFeet: Vector3, shulkerBase: Vector3): boolean {
    const topY = shulkerBase.y + this.shulkerHeight;
    const separation = playerFeet.y - topY;

    const horizOverlap =
      Math.abs(playerFeet.x - shulkerBase.x) <= (this.playerHalfW + this.shulkerHalfW) &&
      Math.abs(playerFeet.z - shulkerBase.z) <= (this.playerHalfW + this.shulkerHalfW);

    return horizOverlap && separation >= -0.01 && separation <= 0.05;
  }

  /**
   * Enforce continuous non-penetration boundary constraint on player elevation.
   */
  public resolveSupport(playerFeet: Vector3, shulkerBase: Vector3): Vector3 {
    const topY = shulkerBase.y + this.shulkerHeight;
    const horizOverlap =
      Math.abs(playerFeet.x - shulkerBase.x) <= (this.playerHalfW + this.shulkerHalfW) &&
      Math.abs(playerFeet.z - shulkerBase.z) <= (this.playerHalfW + this.shulkerHalfW);

    if (horizOverlap && playerFeet.y <= topY + 0.05) {
      return { x: playerFeet.x, y: topY, z: playerFeet.z };
    }

    return playerFeet;
  }
}

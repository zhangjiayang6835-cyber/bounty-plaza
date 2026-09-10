/**
 * Type declarations and data models for Bedrock physics and potion effects.
 */

/**
 * Three-dimensional kinematic vector.
 */
export interface KinematicVector3 {
  x: number;
  y: number;
  z: number;
}

/**
 * Potion effect descriptor for 1-tick cycling and status mitigation.
 */
export interface BedrockPotionEffect {
  type: string;
  amplifier: number;
  duration: number;
}

/**
 * Result of fall damage impact resolution.
 */
export interface FallDamageResult {
  fallDistance: number;
  impactVelocityY: number;
  safeThreshold: number;
  rawDamage: number;
  absorptionDamageAbsorbed: number;
  customShieldDamageAbsorbed: number;
  finalHealthDamage: number;
  remainingHealth: number;
  lethalPrevented: boolean;
  dampeningMultiplier: number;
}

/**
 * Physics configuration constants matching Bedrock server kinematics.
 */
export interface BedrockPhysicsConstants {
  gravity: number;
  airDrag: number;
  baseSafeThreshold: number;
  baseMaxHealth: number;
  absorptionBonusPerAmplifier: number;
  amplifierScaleFactor: number;
}

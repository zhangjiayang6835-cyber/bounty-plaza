/**
 * @file Node.js mirror for OmniBlocks backflip kinematics and quadrillion settlement.
 */

const crypto = require("node:crypto");

const AccountFollowStatus = Object.freeze({
  PENDING: "PENDING",
  VERIFIED: "VERIFIED",
  REJECTED: "REJECTED",
  EXPIRED: "EXPIRED",
  NOT_FOLLOWING: "NOT_FOLLOWING"
});

const BackflipPhase = Object.freeze({
  PREPARATION: "PREPARATION",
  TAKEOFF: "TAKEOFF",
  INVERTED: "INVERTED",
  TUCK: "TUCK",
  EXTENSION: "EXTENSION",
  LANDING: "LANDING",
  STABILIZED: "STABILIZED"
});

const FailureReason = Object.freeze({
  INSUFFICIENT_ROTATION: "INSUFFICIENT_ROTATION",
  INSUFFICIENT_HEIGHT: "INSUFFICIENT_HEIGHT",
  INSUFFICIENT_AIRTIME: "INSUFFICIENT_AIRTIME",
  NO_INVERSION: "NO_INVERSION",
  UNSTABLE_LANDING: "UNSTABLE_LANDING",
  AXIAL_DEVIATION: "AXIAL_DEVIATION",
  TEMPORAL_TIMEOUT: "TEMPORAL_TIMEOUT",
  UNVERIFIED_FOLLOWER: "UNVERIFIED_FOLLOWER",
  ZERO_SETTLEMENT: "ZERO_SETTLEMENT"
});

class GitHubFollowVerifier {
  static CANONICAL_TARGET = "unconstructable13";
  static USERNAME_PATTERN = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;

  constructor(authDescriptor = "") {
    this.authDescriptor = authDescriptor;
  }

  static normalizeTargetAccount(rawTarget) {
    const cleaned = String(rawTarget || "").trim().toLowerCase();
    if (cleaned === "githuub" || cleaned === "github" || cleaned === "unconstructable13") {
      return GitHubFollowVerifier.CANONICAL_TARGET;
    }
    return String(rawTarget || "").trim();
  }

  static isValidUsername(username) {
    if (!username) return false;
    return GitHubFollowVerifier.USERNAME_PATTERN.test(username);
  }

  verifyWebhookSignature(payloadBuffer, signatureHeader) {
    if (!this.authDescriptor || !signatureHeader) return false;
    if (!signatureHeader.startsWith("sha256=")) return false;

    const expectedSig = signatureHeader.slice(7);
    const hmac = crypto.createHmac("sha256", this.authDescriptor);
    hmac.update(payloadBuffer);
    const computedSig = hmac.digest("hex");

    if (computedSig.length !== expectedSig.length) return false;
    return crypto.timingSafeEqual(Buffer.from(computedSig), Buffer.from(expectedSig));
  }

  verifyFollowerRelationship(followerUsername, targetAccount, followedAtEpoch, issueCreatedEpoch, maxDelaySec = 1800.0) {
    const isValid = GitHubFollowVerifier.isValidUsername(followerUsername);
    const normTarget = GitHubFollowVerifier.normalizeTargetAccount(targetAccount);
    const elapsedSec = followedAtEpoch - issueCreatedEpoch;

    const rawToken = `${followerUsername}:${normTarget}:${followedAtEpoch.toFixed(3)}`;
    const hash = crypto.createHash("sha256").update(rawToken).digest("hex");

    if (!isValid) {
      return {
        username: followerUsername,
        targetAccount: normTarget,
        followedAtEpoch,
        verificationHash: hash,
        isVerified: false,
        status: AccountFollowStatus.REJECTED
      };
    }

    if (elapsedSec < 0.0 || elapsedSec > maxDelaySec) {
      return {
        username: followerUsername,
        targetAccount: normTarget,
        followedAtEpoch,
        verificationHash: hash,
        isVerified: false,
        status: AccountFollowStatus.EXPIRED
      };
    }

    return {
      username: followerUsername,
      targetAccount: normTarget,
      followedAtEpoch,
      verificationHash: hash,
      isVerified: true,
      status: AccountFollowStatus.VERIFIED
    };
  }
}

class BackflipKinematicsEngine {
  static MIN_TOTAL_ROTATION_DEG = 330.0;
  static MAX_TOTAL_ROTATION_DEG = 410.0;
  static MIN_APEX_HEIGHT_M = 0.25;
  static MIN_AIRTIME_SEC = 0.40;
  static MAX_AXIAL_DRIFT_DEG = 35.0;
  static MAX_LANDING_ANGLE_ERROR_DEG = 25.0;
  static MIN_STABILITY_PASS_SCORE = 0.70;

  static analyzeInertialTelemetry(readings) {
    if (!readings || readings.length < 5) {
      return {
        isSuccessful: false,
        peakPitchDeg: 0.0,
        totalRotationDeg: 0.0,
        maxAltitudeM: 0.0,
        airtimeS: 0.0,
        stabilityScore: 0.0,
        detectedPhase: BackflipPhase.PREPARATION,
        failureReasons: [FailureReason.INSUFFICIENT_AIRTIME]
      };
    }

    const initialAltitude = readings[0].altitudeM;
    let maxAltitude = readings[0].altitudeM;
    let peakPitch = 0.0;
    let maxAxialDrift = 0.0;
    let cumulativeRotation = 0.0;
    let invertedReached = false;
    const airborneReadings = [];

    for (let i = 0; i < readings.length; i++) {
      const r = readings[i];
      if (r.altitudeM > maxAltitude) maxAltitude = r.altitudeM;

      const absPitch = Math.abs(r.pitchDeg);
      if (absPitch > peakPitch) peakPitch = absPitch;

      if (absPitch >= 140.0 && absPitch <= 220.0) {
        invertedReached = true;
      }

      const drift = Math.max(Math.abs(r.rollDeg), Math.abs(r.yawDeg));
      if (drift > maxAxialDrift) maxAxialDrift = drift;

      if (r.altitudeM > initialAltitude + 0.05) {
        airborneReadings.push(r);
      }

      if (i > 0) {
        const dtSec = (r.timestampMs - readings[i - 1].timestampMs) / 1000.0;
        if (dtSec > 0) {
          cumulativeRotation += Math.abs(r.gyroPitchRate) * dtSec * (180.0 / Math.PI);
        }
      }
    }

    const apexHeight = maxAltitude - initialAltitude;
    const airtimeSec = airborneReadings.length >= 2
      ? (airborneReadings[airborneReadings.length - 1].timestampMs - airborneReadings[0].timestampMs) / 1000.0
      : (readings[readings.length - 1].timestampMs - readings[0].timestampMs) / 1000.0;

    const finalReading = readings[readings.length - 1];
    let landingPitchError = Math.abs(Math.abs(finalReading.pitchDeg) % 360.0);
    if (landingPitchError > 180.0) landingPitchError = 360.0 - landingPitchError;

    const pitchFactor = Math.max(0.0, 1.0 - (landingPitchError / 30.0));
    const driftFactor = Math.max(0.0, 1.0 - (maxAxialDrift / 40.0));
    const accelError = Math.abs(finalReading.accelVertical - 9.81);
    const accelFactor = Math.max(0.0, 1.0 - (accelError / 25.0));
    const stabilityScore = Math.min(1.0, Math.max(0.0, (pitchFactor * 0.5) + (driftFactor * 0.3) + (accelFactor * 0.2)));

    const failureReasons = [];
    if (cumulativeRotation < BackflipKinematicsEngine.MIN_TOTAL_ROTATION_DEG || cumulativeRotation > BackflipKinematicsEngine.MAX_TOTAL_ROTATION_DEG) {
      failureReasons.push(FailureReason.INSUFFICIENT_ROTATION);
    }
    if (apexHeight < BackflipKinematicsEngine.MIN_APEX_HEIGHT_M) {
      failureReasons.push(FailureReason.INSUFFICIENT_HEIGHT);
    }
    if (airtimeSec < BackflipKinematicsEngine.MIN_AIRTIME_SEC) {
      failureReasons.push(FailureReason.INSUFFICIENT_AIRTIME);
    }
    if (!invertedReached) {
      failureReasons.push(FailureReason.NO_INVERSION);
    }
    if (maxAxialDrift > BackflipKinematicsEngine.MAX_AXIAL_DRIFT_DEG) {
      failureReasons.push(FailureReason.AXIAL_DEVIATION);
    }
    if (stabilityScore < BackflipKinematicsEngine.MIN_STABILITY_PASS_SCORE || landingPitchError > BackflipKinematicsEngine.MAX_LANDING_ANGLE_ERROR_DEG) {
      failureReasons.push(FailureReason.UNSTABLE_LANDING);
    }

    const isSuccessful = failureReasons.length === 0;

    return {
      isSuccessful,
      peakPitchDeg: Number(peakPitch.toFixed(2)),
      totalRotationDeg: Number(cumulativeRotation.toFixed(2)),
      maxAltitudeM: Number(maxAltitude.toFixed(3)),
      airtimeS: Number(airtimeSec.toFixed(3)),
      stabilityScore: Number(stabilityScore.toFixed(3)),
      detectedPhase: isSuccessful ? BackflipPhase.STABILIZED : BackflipPhase.LANDING,
      failureReasons
    };
  }
}

class QuadrillionSettlementEngine {
  static NOMINAL_BOUNTY_USD_STR = "239398281948585883";
  static NOMINAL_BOUNTY_USD_BIGINT = BigInt("239398281948585883");
  static EVM_REGEX = /^0x[a-fA-F0-9]{40}$/;
  static STELLAR_REGEX = /^G[A-Z2-7]{55}$/;
  static CANONICAL_EVM = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89";
  static CANONICAL_STELLAR = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC";

  static calculateSettlementBigInt(nominalUsdBigInt = QuadrillionSettlementEngine.NOMINAL_BOUNTY_USD_BIGINT) {
    const scale = 10000n;
    const coinsTotal = (nominalUsdBigInt * 12500n) / scale;
    const contributorRatioScaled = 8500n;
    const contributorCoins = (coinsTotal * contributorRatioScaled) / scale;
    const coinRedemptionScaled = 7200n;
    const contributorCashScaled = (contributorCoins * coinRedemptionScaled) / scale;
    const platformFeeScaled = nominalUsdBigInt - contributorCashScaled;

    return {
      nominalUsd: nominalUsdBigInt.toString(),
      coinsTotal: coinsTotal.toString(),
      contributorRatio: "0.85",
      contributorCoins: contributorCoins.toString(),
      contributorCashUsd: contributorCashScaled.toString(),
      platformFeeUsd: platformFeeScaled.toString()
    };
  }

  static validateEvmAddress(address) {
    if (!address) return false;
    return QuadrillionSettlementEngine.EVM_REGEX.test(address);
  }

  static validateStellarAddress(address) {
    if (!address) return false;
    return QuadrillionSettlementEngine.STELLAR_REGEX.test(address);
  }
}

module.exports = {
  AccountFollowStatus,
  BackflipPhase,
  FailureReason,
  GitHubFollowVerifier,
  BackflipKinematicsEngine,
  QuadrillionSettlementEngine
};

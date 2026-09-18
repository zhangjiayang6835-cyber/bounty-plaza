const assert = require("node:assert");
const crypto = require("node:crypto");
const {
  AccountFollowStatus,
  FailureReason,
  GitHubFollowVerifier,
  BackflipKinematicsEngine,
  QuadrillionSettlementEngine
} = require("../src/omni_backflip");

function testGitHubFollowVerifier() {
  const verifier = new GitHubFollowVerifier("test-signing-key");

  assert.strictEqual(
    GitHubFollowVerifier.normalizeTargetAccount("GitHuub"),
    "unconstructable13"
  );
  assert.strictEqual(
    GitHubFollowVerifier.normalizeTargetAccount("GitHub"),
    "unconstructable13"
  );
  assert.strictEqual(
    GitHubFollowVerifier.normalizeTargetAccount("other-account"),
    "other-account"
  );

  assert.strictEqual(GitHubFollowVerifier.isValidUsername("valid-user-1"), true);
  assert.strictEqual(GitHubFollowVerifier.isValidUsername(""), false);

  const payload = Buffer.from(JSON.stringify({ action: "followed" }));
  const hmac = crypto.createHmac("sha256", "test-signing-key").update(payload).digest("hex");
  const signatureHeader = `sha256=${hmac}`;
  assert.strictEqual(verifier.verifyWebhookSignature(payload, signatureHeader), true);
  assert.strictEqual(verifier.verifyWebhookSignature(payload, "sha256=invalid"), false);

  const baseEpoch = 1700000000.0;
  const validRecord = verifier.verifyFollowerRelationship(
    "alice",
    "GitHuub",
    baseEpoch + 600.0,
    baseEpoch
  );
  assert.strictEqual(validRecord.isVerified, true);
  assert.strictEqual(validRecord.status, AccountFollowStatus.VERIFIED);
  assert.strictEqual(validRecord.targetAccount, "unconstructable13");

  const expiredRecord = verifier.verifyFollowerRelationship(
    "bob",
    "GitHuub",
    baseEpoch + 2000.0,
    baseEpoch
  );
  assert.strictEqual(expiredRecord.isVerified, false);
  assert.strictEqual(expiredRecord.status, AccountFollowStatus.EXPIRED);
}

function testKinematicsEngine() {
  const readings = [];
  const samples = 40;
  const dt = 20.0;

  for (let i = 0; i < samples; i++) {
    const t = i * dt;
    const progress = t / (samples * dt);
    const pitch = progress * 360.0;
    const altitude = 1.0 + 0.6 * Math.sin(progress * Math.PI);
    readings.push({
      timestampMs: t,
      pitchDeg: pitch,
      rollDeg: 1.0,
      yawDeg: 1.0,
      gyroPitchRate: (360.0 * Math.PI / 180.0) / 0.8,
      accelVertical: 9.81,
      altitudeM: altitude
    });
  }

  const result = BackflipKinematicsEngine.analyzeInertialTelemetry(readings);
  assert.strictEqual(result.isSuccessful, true);
  assert.strictEqual(result.failureReasons.length, 0);

  const failedReadings = readings.map(r => ({
    ...r,
    pitchDeg: r.pitchDeg * 0.5,
    gyroPitchRate: r.gyroPitchRate * 0.5
  }));
  const failResult = BackflipKinematicsEngine.analyzeInertialTelemetry(failedReadings);
  assert.strictEqual(failResult.isSuccessful, false);
  assert.ok(failResult.failureReasons.includes(FailureReason.INSUFFICIENT_ROTATION));
}

function testQuadrillionSettlementEngine() {
  const calc = QuadrillionSettlementEngine.calculateSettlementBigInt();
  assert.strictEqual(calc.nominalUsd, "239398281948585883");
  assert.strictEqual(calc.coinsTotal, "299247852435732353");
  assert.strictEqual(calc.contributorRatio, "0.85");
  assert.strictEqual(calc.contributorCoins, "254360674570372500");
  assert.strictEqual(calc.contributorCashUsd, "183139685690668200");
  assert.strictEqual(calc.platformFeeUsd, "56258596257917683");

  assert.strictEqual(
    QuadrillionSettlementEngine.validateEvmAddress(QuadrillionSettlementEngine.CANONICAL_EVM),
    true
  );
  assert.strictEqual(
    QuadrillionSettlementEngine.validateEvmAddress("0xinvalid"),
    false
  );
  assert.strictEqual(
    QuadrillionSettlementEngine.validateStellarAddress(QuadrillionSettlementEngine.CANONICAL_STELLAR),
    true
  );
  assert.strictEqual(
    QuadrillionSettlementEngine.validateStellarAddress("G123"),
    false
  );
}

function runAllTests() {
  testGitHubFollowVerifier();
  testKinematicsEngine();
  testQuadrillionSettlementEngine();
  process.stdout.write("All Node.js tests passed successfully.\n");
}

runAllTests();

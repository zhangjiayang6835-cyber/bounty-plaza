/**
 * @file Unit tests for Node.js OmniUniverse engine mirror.
 */

const assert = require("assert");
const {
  Vector3D,
  CelestialType,
  SpectralClass,
  GalaxyMorphology,
  CosmicEpoch,
  GravitationalSimulator,
  CosmologicalEngine,
  DeterministicRNG,
  SpatialGridIndex,
  ProceduralUniverseGenerator,
  QuadrillionSettlementEngine,
  OmniUniverse,
  SOLAR_MASS,
  ASTRONOMICAL_UNIT,
  CMB_TEMPERATURE_NOW,
  HUBBLE_CONSTANT,
} = require("../src/omni_universe.js");

function testVectorMath() {
  const v1 = new Vector3D(1, 2, 3);
  const v2 = new Vector3D(4, 5, 6);

  const add = v1.add(v2);
  assert.strictEqual(add.x, 5);
  assert.strictEqual(add.y, 7);
  assert.strictEqual(add.z, 9);

  const sub = v2.sub(v1);
  assert.strictEqual(sub.x, 3);
  assert.strictEqual(sub.y, 3);
  assert.strictEqual(sub.z, 3);

  assert.strictEqual(v1.magnitudeSquared(), 14);
  assert.strictEqual(v1.dot(v2), 32);

  const cross = v1.cross(v2);
  assert.strictEqual(cross.x, -3);
  assert.strictEqual(cross.y, 6);
  assert.strictEqual(cross.z, -3);
}

function testGravitationalPhysics() {
  const rsSun = GravitationalSimulator.schwarzschildRadius(SOLAR_MASS);
  assert(rsSun > 2900 && rsSun < 3000);

  const earthOrbV = GravitationalSimulator.keplerianOrbitalVelocity(SOLAR_MASS, ASTRONOMICAL_UNIT);
  assert(earthOrbV > 29000 && earthOrbV < 31000);

  const vEsc = GravitationalSimulator.escapeVelocity(SOLAR_MASS, ASTRONOMICAL_UNIT);
  assert(Math.abs(vEsc - Math.sqrt(2) * earthOrbV) < 1.0);

  const lumSun = GravitationalSimulator.stellarLuminosityFromMass(SOLAR_MASS);
  assert(Math.abs(lumSun - 3.828e26) < 1e20);

  const tempSun = GravitationalSimulator.effectiveTemperature(3.828e26, 6.957e8);
  assert(tempSun > 5700 && tempSun < 5850);

  assert.strictEqual(GravitationalSimulator.determineSpectralClass(tempSun), SpectralClass.G);
  assert.strictEqual(GravitationalSimulator.determineSpectralClass(35000), SpectralClass.O);
}

function testCosmology() {
  const cosmo = new CosmologicalEngine();
  const h0 = cosmo.hubbleParameterAtRedshift(0.0);
  assert(Math.abs(h0 - HUBBLE_CONSTANT) < 0.1);

  const tCmb1 = CosmologicalEngine.cmbTemperatureAtRedshift(1.0);
  assert(Math.abs(tCmb1 - 2.0 * CMB_TEMPERATURE_NOW) < 1e-4);

  assert.strictEqual(CosmologicalEngine.getEpochForAge(1e-40), CosmicEpoch.INFLATIONARY);
  assert.strictEqual(CosmologicalEngine.getEpochForAge(1e17), CosmicEpoch.STELLIFEROUS);
  assert.strictEqual(CosmologicalEngine.getEpochForAge(1e115), CosmicEpoch.HEAT_DEATH);

  const energy = cosmo.cosmicEnergyInventory();
  assert(energy.dark_energy > 0.65 && energy.dark_energy < 0.72);
}

function testSpatialGrid() {
  const grid = new SpatialGridIndex(10.0 * ASTRONOMICAL_UNIT);
  const center = {
    entity_id: "center",
    position: new Vector3D(0, 0, 0),
  };
  const near = {
    entity_id: "near",
    position: new Vector3D(1.0 * ASTRONOMICAL_UNIT, 0, 0),
  };
  const far = {
    entity_id: "far",
    position: new Vector3D(50.0 * ASTRONOMICAL_UNIT, 0, 0),
  };

  grid.insert(center);
  grid.insert(near);
  grid.insert(far);

  const found = grid.queryRadius(new Vector3D(0, 0, 0), 5.0 * ASTRONOMICAL_UNIT);
  const ids = found.map((e) => e.entity_id);
  assert(ids.includes("center"));
  assert(ids.includes("near"));
  assert(!ids.includes("far"));
}

function testProceduralGeneration() {
  const gen1 = new ProceduralUniverseGenerator("seed_node_test");
  const gen2 = new ProceduralUniverseGenerator("seed_node_test");

  const g1 = gen1.generateGalaxy("g1", "Andromeda", GalaxyMorphology.SPIRAL, null, 3);
  const g2 = gen2.generateGalaxy("g1", "Andromeda", GalaxyMorphology.SPIRAL, null, 3);

  assert.strictEqual(g1.length, g2.length);
  for (let i = 0; i < g1.length; i++) {
    assert.strictEqual(g1[i].entity_id, g2[i].entity_id);
    assert.strictEqual(g1[i].mass, g2[i].mass);
    assert.strictEqual(g1[i].position.x, g2[i].position.x);
  }
}

function testQuadrillionSettlement() {
  const evm = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89";
  const stellar = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC";

  assert.strictEqual(QuadrillionSettlementEngine.validateEvmAddress(evm), true);
  assert.strictEqual(QuadrillionSettlementEngine.validateStellarAddress(stellar), true);
  assert.strictEqual(QuadrillionSettlementEngine.validateEvmAddress("0xinvalid"), false);
  assert.strictEqual(QuadrillionSettlementEngine.validateStellarAddress("bad_key"), false);

  const receipt = QuadrillionSettlementEngine.calculateSettlement(evm, stellar);

  assert.strictEqual(receipt.issue_id, 1575);
  assert.strictEqual(receipt.nominal_bounty_usd, "999999999999999999");
  assert.strictEqual(receipt.platform_coins_minted, "1250000000000000000");
  assert.strictEqual(receipt.contributor_share_ratio, "0.85");
  assert.strictEqual(receipt.contributor_coins_credited, "1062500000000000000");
  assert.strictEqual(receipt.net_contributor_payout_usd, "765000000000000000.00");
  assert.strictEqual(receipt.platform_treasury_fee_usd, "234999999999999999.00");
  assert.strictEqual(receipt.evm_payout_address, evm);
  assert.strictEqual(receipt.stellar_payout_address, stellar);
  assert.strictEqual(receipt.settlement_hash.length, 64);
}

function testOmniUniverseLifecycle() {
  const cosmos = new OmniUniverse("node_universe_genesis");
  cosmos.spawnGalaxy("Triangulum", "spiral", 3);

  const entities = cosmos.getAllEntities();
  assert(entities.length > 3);

  const initialSummary = cosmos.getSummary();
  assert.strictEqual(initialSummary.epoch, CosmicEpoch.STELLIFEROUS);
  assert(initialSummary.total_entities > 3);

  cosmos.step(50.0, 2);
  const updatedSummary = cosmos.getSummary();
  assert(updatedSummary.age_seconds > initialSummary.age_seconds);

  const receipt = cosmos.executeBountySettlement(
    "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89",
    "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
  );
  assert.strictEqual(receipt.net_contributor_payout_usd, "765000000000000000.00");
}

function runAll() {
  testVectorMath();
  testGravitationalPhysics();
  testCosmology();
  testSpatialGrid();
  testProceduralGeneration();
  testQuadrillionSettlement();
  testOmniUniverseLifecycle();
  console.log("All 7 Node.js test suites passed successfully.");
}

runAll();

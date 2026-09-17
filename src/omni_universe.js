/**
 * @file OmniUniverse simulation engine and cosmological settlement runtime.
 */

const crypto = require("crypto");

const SPEED_OF_LIGHT = 299792458.0;
const GRAVITATIONAL_CONSTANT = 6.67430e-11;
const PLANCK_CONSTANT = 6.62607015e-34;
const REDUCED_PLANCK_CONSTANT = 1.054571817e-34;
const BOLTZMANN_CONSTANT = 1.380649e-23;
const STEFAN_BOLTZMANN_CONSTANT = 5.670374419e-8;

const SOLAR_MASS = 1.98847e30;
const SOLAR_RADIUS = 6.957e8;
const SOLAR_LUMINOSITY = 3.828e26;
const EARTH_MASS = 5.9722e24;
const EARTH_RADIUS = 6.371e6;

const ASTRONOMICAL_UNIT = 1.495978707e11;
const LIGHT_YEAR = 9.4607304725808e15;
const PARSEC = 3.08567758149137e16;
const KILOPARSEC = 3.08567758149137e19;
const MEGAPARSEC = 3.08567758149137e22;

const HUBBLE_CONSTANT = 70.0;
const HUBBLE_CONSTANT_SI = (70.0 * 1000.0) / MEGAPARSEC;
const CRITICAL_DENSITY = (3.0 * (HUBBLE_CONSTANT_SI ** 2)) / (8.0 * Math.PI * GRAVITATIONAL_CONSTANT);
const CMB_TEMPERATURE_NOW = 2.7255;
const UNIVERSE_AGE_YEARS = 13.787e9;
const UNIVERSE_AGE_SECONDS = 13.787e9 * 365.25 * 86400.0;

class Vector3D {
  /**
   * @param {number} x
   * @param {number} y
   * @param {number} z
   */
  constructor(x = 0.0, y = 0.0, z = 0.0) {
    this.x = Number(x);
    this.y = Number(y);
    this.z = Number(z);
  }

  add(other) {
    return new Vector3D(this.x + other.x, this.y + other.y, this.z + other.z);
  }

  sub(other) {
    return new Vector3D(this.x - other.x, this.y - other.y, this.z - other.z);
  }

  scale(scalar) {
    return new Vector3D(this.x * scalar, this.y * scalar, this.z * scalar);
  }

  div(scalar) {
    if (scalar === 0.0) {
      throw new Error("Division by zero in Vector3D.");
    }
    return new Vector3D(this.x / scalar, this.y / scalar, this.z / scalar);
  }

  magnitudeSquared() {
    return this.x * this.x + this.y * this.y + this.z * this.z;
  }

  magnitude() {
    return Math.sqrt(this.magnitudeSquared());
  }

  distanceTo(other) {
    return this.sub(other).magnitude();
  }

  distanceSquaredTo(other) {
    return this.sub(other).magnitudeSquared();
  }

  normalize() {
    const mag = this.magnitude();
    return mag === 0.0 ? new Vector3D(0.0, 0.0, 0.0) : this.div(mag);
  }

  dot(other) {
    return this.x * other.x + this.y * other.y + this.z * other.z;
  }

  cross(other) {
    return new Vector3D(
      this.y * other.z - this.z * other.y,
      this.z * other.x - this.x * other.z,
      this.x * other.y - this.y * other.x
    );
  }

  toJSON() {
    return { x: this.x, y: this.y, z: this.z };
  }

  static fromJSON(data) {
    return new Vector3D(data?.x ?? 0.0, data?.y ?? 0.0, data?.z ?? 0.0);
  }
}

const CelestialType = Object.freeze({
  SUPERCLUSTER: "supercluster",
  GALAXY: "galaxy",
  NEBULA: "nebula",
  STAR: "star",
  BLACK_HOLE: "black_hole",
  NEUTRON_STAR: "neutron_star",
  PLANET: "planet",
  MOON: "moon",
  ASTEROID: "asteroid",
  COMET: "comet",
});

const SpectralClass = Object.freeze({
  O: "O",
  B: "B",
  A: "A",
  F: "F",
  G: "G",
  K: "K",
  M: "M",
  WHITE_DWARF: "D",
  COMPACT: "COMPACT",
});

const GalaxyMorphology = Object.freeze({
  SPIRAL: "spiral",
  BARRED_SPIRAL: "barred_spiral",
  ELLIPTICAL: "elliptical",
  IRREGULAR: "irregular",
});

const CosmicEpoch = Object.freeze({
  PLANCK: "planck",
  INFLATIONARY: "inflationary",
  ELECTROWEAK: "electroweak",
  QUARK_GLUON: "quark_gluon",
  HADRON: "hadron",
  LEPTON: "lepton",
  PHOTON_NUCLEOSYNTHESIS: "photon_nucleosynthesis",
  RECOMBINATION_CMB: "recombination_cmb",
  DARK_AGES: "dark_ages",
  REIONIZATION: "reionization",
  STELLIFEROUS: "stelliferous",
  DEGENERATE: "degenerate",
  BLACK_HOLE_ERA: "black_hole_era",
  HEAT_DEATH: "heat_death",
});

class CelestialEntity {
  /**
   * @param {object} params
   */
  constructor({
    entity_id,
    name,
    entity_type,
    mass,
    radius,
    position = new Vector3D(),
    velocity = new Vector3D(),
    luminosity = 0.0,
    temperature = 0.0,
    spectral_class = null,
    parent_id = null,
    composition = {},
    metadata = {},
    children_ids = [],
  }) {
    this.entity_id = String(entity_id);
    this.name = String(name);
    this.entity_type = entity_type;
    this.mass = Number(mass);
    this.radius = Number(radius);
    this.position = position instanceof Vector3D ? position : Vector3D.fromJSON(position);
    this.velocity = velocity instanceof Vector3D ? velocity : Vector3D.fromJSON(velocity);
    this.luminosity = Number(luminosity);
    this.temperature = Number(temperature);
    this.spectral_class = spectral_class;
    this.parent_id = parent_id;
    this.composition = { ...composition };
    this.metadata = { ...metadata };
    this.children_ids = [...children_ids];
  }

  toJSON() {
    return {
      entity_id: this.entity_id,
      name: this.name,
      entity_type: this.entity_type,
      mass: this.mass,
      radius: this.radius,
      position: this.position.toJSON(),
      velocity: this.velocity.toJSON(),
      luminosity: this.luminosity,
      temperature: this.temperature,
      spectral_class: this.spectral_class,
      parent_id: this.parent_id,
      composition: this.composition,
      metadata: this.metadata,
      children_ids: this.children_ids,
    };
  }

  static fromJSON(data) {
    return new CelestialEntity({
      ...data,
      position: Vector3D.fromJSON(data.position),
      velocity: Vector3D.fromJSON(data.velocity),
    });
  }
}

class GravitationalSimulator {
  /**
   * @param {number} softeningLength
   */
  constructor(softeningLength = 1e6) {
    this.softeningLength = Number(softeningLength);
    this.softeningSquared = this.softeningLength * this.softeningLength;
  }

  computeAcceleration(target, bodies) {
    let accel = new Vector3D(0.0, 0.0, 0.0);
    const targetPos = target.position;

    for (const body of bodies) {
      if (body.entity_id === target.entity_id) {
        continue;
      }
      const delta = body.position.sub(targetPos);
      const distSq = delta.magnitudeSquared() + this.softeningSquared;
      const dist = Math.sqrt(distSq);
      if (dist === 0.0) {
        continue;
      }
      const forceScalar = (GRAVITATIONAL_CONSTANT * body.mass) / (distSq * dist);
      accel = accel.add(delta.scale(forceScalar));
    }
    return accel;
  }

  stepNBody(bodies, dt) {
    if (!bodies || bodies.length === 0 || dt === 0.0) {
      return;
    }
    const accelerations = bodies.map((b) => this.computeAcceleration(b, bodies));

    for (let i = 0; i < bodies.length; i++) {
      const b = bodies[i];
      const a = accelerations[i];
      b.position = b.position.add(b.velocity.scale(dt)).add(a.scale(0.5 * dt * dt));
    }

    const newAccelerations = bodies.map((b) => this.computeAcceleration(b, bodies));
    const cLimit = 0.9999 * SPEED_OF_LIGHT;

    for (let i = 0; i < bodies.length; i++) {
      const b = bodies[i];
      const aAvg = accelerations[i].add(newAccelerations[i]).scale(0.5);
      let newVel = b.velocity.add(aAvg.scale(dt));
      if (newVel.magnitude() > cLimit) {
        newVel = newVel.normalize().scale(cLimit);
      }
      b.velocity = newVel;
    }
  }

  static schwarzschildRadius(mass) {
    if (mass <= 0.0) return 0.0;
    return (2.0 * GRAVITATIONAL_CONSTANT * mass) / (SPEED_OF_LIGHT * SPEED_OF_LIGHT);
  }

  static keplerianOrbitalVelocity(centralMass, orbitalRadius) {
    if (centralMass <= 0.0 || orbitalRadius <= 0.0) return 0.0;
    return Math.sqrt((GRAVITATIONAL_CONSTANT * centralMass) / orbitalRadius);
  }

  static orbitalPeriod(centralMass, semiMajorAxis) {
    if (centralMass <= 0.0 || semiMajorAxis <= 0.0) return 0.0;
    return 2.0 * Math.PI * Math.sqrt((semiMajorAxis ** 3) / (GRAVITATIONAL_CONSTANT * centralMass));
  }

  static escapeVelocity(centralMass, radius) {
    if (centralMass <= 0.0 || radius <= 0.0) return 0.0;
    return Math.sqrt((2.0 * GRAVITATIONAL_CONSTANT * centralMass) / radius);
  }

  static stellarLuminosityFromMass(massKg) {
    if (massKg <= 0.0) return 0.0;
    const mSolar = massKg / SOLAR_MASS;
    return SOLAR_LUMINOSITY * (mSolar ** 3.5);
  }

  static effectiveTemperature(luminosityWatts, radiusMeters) {
    if (luminosityWatts <= 0.0 || radiusMeters <= 0.0) return 0.0;
    const surfaceArea = 4.0 * Math.PI * (radiusMeters ** 2);
    const flux = luminosityWatts / surfaceArea;
    return (flux / STEFAN_BOLTZMANN_CONSTANT) ** 0.25;
  }

  static determineSpectralClass(temperatureKelvin) {
    if (temperatureKelvin >= 30000.0) return SpectralClass.O;
    if (temperatureKelvin >= 10000.0) return SpectralClass.B;
    if (temperatureKelvin >= 7500.0) return SpectralClass.A;
    if (temperatureKelvin >= 6000.0) return SpectralClass.F;
    if (temperatureKelvin >= 5200.0) return SpectralClass.G;
    if (temperatureKelvin >= 3700.0) return SpectralClass.K;
    if (temperatureKelvin >= 2400.0) return SpectralClass.M;
    return SpectralClass.WHITE_DWARF;
  }
}

class CosmologicalEngine {
  static EPOCH_THRESHOLDS = [
    [1e-43, CosmicEpoch.PLANCK],
    [1e-32, CosmicEpoch.INFLATIONARY],
    [1e-12, CosmicEpoch.ELECTROWEAK],
    [1e-6, CosmicEpoch.QUARK_GLUON],
    [1.0, CosmicEpoch.HADRON],
    [10.0, CosmicEpoch.LEPTON],
    [1200.0, CosmicEpoch.PHOTON_NUCLEOSYNTHESIS],
    [380000.0 * 365.25 * 86400.0, CosmicEpoch.RECOMBINATION_CMB],
    [100e6 * 365.25 * 86400.0, CosmicEpoch.DARK_AGES],
    [1e9 * 365.25 * 86400.0, CosmicEpoch.REIONIZATION],
    [100e12 * 365.25 * 86400.0, CosmicEpoch.STELLIFEROUS],
    [1e40 * 365.25 * 86400.0, CosmicEpoch.DEGENERATE],
    [1e100 * 365.25 * 86400.0, CosmicEpoch.BLACK_HOLE_ERA],
  ];

  constructor(hubbleConstant = HUBBLE_CONSTANT, omegaMatter = 0.315, omegaLambda = 0.685, omegaRadiation = 9.0e-5) {
    this.hubbleConstant = Number(hubbleConstant);
    this.omegaMatter = Number(omegaMatter);
    this.omegaLambda = Number(omegaLambda);
    this.omegaRadiation = Number(omegaRadiation);
  }

  static getEpochForAge(ageSeconds) {
    for (const [limit, epoch] of CosmologicalEngine.EPOCH_THRESHOLDS) {
      if (ageSeconds < limit) {
        return epoch;
      }
    }
    return CosmicEpoch.HEAT_DEATH;
  }

  hubbleParameterAtRedshift(redshift) {
    if (redshift < -1.0) {
      throw new Error("Redshift cannot be less than -1.0.");
    }
    const termM = this.omegaMatter * ((1.0 + redshift) ** 3);
    const termR = this.omegaRadiation * ((1.0 + redshift) ** 4);
    const termL = this.omegaLambda;
    return this.hubbleConstant * Math.sqrt(termM + termR + termL);
  }

  static cmbTemperatureAtRedshift(redshift) {
    if (redshift < -1.0) throw new Error("Redshift cannot be less than -1.0.");
    return CMB_TEMPERATURE_NOW * (1.0 + redshift);
  }

  static cosmicScaleFactor(redshift) {
    if (redshift <= -1.0) throw new Error("Redshift must be greater than -1.0.");
    return 1.0 / (1.0 + redshift);
  }

  cosmicEnergyInventory() {
    const total = this.omegaMatter + this.omegaLambda + this.omegaRadiation;
    return {
      dark_energy: this.omegaLambda / total,
      matter_total: this.omegaMatter / total,
      baryonic_matter: 0.049 / total,
      cold_dark_matter: (this.omegaMatter - 0.049) / total,
      radiation: this.omegaRadiation / total,
    };
  }

  static bekensteinHawkingEntropy(blackHoleMassKg) {
    if (blackHoleMassKg <= 0.0) return 0.0;
    const numerator = 4.0 * Math.PI * BOLTZMANN_CONSTANT * GRAVITATIONAL_CONSTANT * (blackHoleMassKg ** 2);
    const denominator = REDUCED_PLANCK_CONSTANT * SPEED_OF_LIGHT;
    return numerator / denominator;
  }
}

class DeterministicRNG {
  constructor(seed) {
    this.seed = String(seed);
    this.counter = 0;
  }

  nextFloat() {
    const buf = Buffer.alloc(8);
    buf.writeBigUInt64BE(BigInt(this.counter), 0);
    this.counter++;
    const hash = crypto.createHash("sha256").update(this.seed).update(buf).digest();
    const intVal = hash.readBigUInt64BE(0);
    return Number(intVal) / Number(0xffffffffffffffffn);
  }

  uniform(low, high) {
    return low + this.nextFloat() * (high - low);
  }

  randint(low, high) {
    return Math.floor(low + this.nextFloat() * (high - low + 1));
  }
}

class SpatialGridIndex {
  constructor(cellSize = 100.0 * ASTRONOMICAL_UNIT) {
    this.cellSize = Number(cellSize);
    this.grid = new Map();
  }

  _hashPosition(pos) {
    const cx = Math.floor(pos.x / this.cellSize);
    const cy = Math.floor(pos.y / this.cellSize);
    const cz = Math.floor(pos.z / this.cellSize);
    return `${cx}:${cy}:${cz}`;
  }

  insert(entity) {
    const key = this._hashPosition(entity.position);
    if (!this.grid.has(key)) {
      this.grid.set(key, []);
    }
    this.grid.get(key).push(entity);
  }

  queryRadius(center, radius) {
    const results = [];
    const rSq = radius * radius;
    const minX = Math.floor((center.x - radius) / this.cellSize);
    const maxX = Math.floor((center.x + radius) / this.cellSize);
    const minY = Math.floor((center.y - radius) / this.cellSize);
    const maxY = Math.floor((center.y + radius) / this.cellSize);
    const minZ = Math.floor((center.z - radius) / this.cellSize);
    const maxZ = Math.floor((center.z + radius) / this.cellSize);

    for (let cx = minX; cx <= maxX; cx++) {
      for (let cy = minY; cy <= maxY; cy++) {
        for (let cz = minZ; cz <= maxZ; cz++) {
          const key = `${cx}:${cy}:${cz}`;
          const bucket = this.grid.get(key);
          if (bucket) {
            for (const entity of bucket) {
              if (entity.position.distanceSquaredTo(center) <= rSq) {
                results.push(entity);
              }
            }
          }
        }
      }
    }
    return results;
  }
}

class ProceduralUniverseGenerator {
  constructor(seed = "omniblocks_universe_genesis") {
    this.seed = String(seed);
    this.rng = new DeterministicRNG(this.seed);
  }

  generateGalaxy(galaxyId, name, morphology = GalaxyMorphology.SPIRAL, center = null, stellarCount = 5) {
    const pos = center instanceof Vector3D ? center : new Vector3D(0.0, 0.0, 0.0);
    const entities = [];

    const smbhMass = 4.154e6 * SOLAR_MASS;
    const smbhRadius = GravitationalSimulator.schwarzschildRadius(smbhMass);
    const smbh = new CelestialEntity({
      entity_id: `${galaxyId}_smbh`,
      name: `${name} Core Black Hole`,
      entity_type: CelestialType.BLACK_HOLE,
      mass: smbhMass,
      radius: smbhRadius,
      position: pos,
      velocity: new Vector3D(0.0, 0.0, 0.0),
      spectral_class: SpectralClass.COMPACT,
      parent_id: galaxyId,
      metadata: { morphology },
    });
    entities.push(smbh);

    for (let i = 0; i < stellarCount; i++) {
      const armAngle = i * ((2.0 * Math.PI) / Math.max(stellarCount, 1)) + this.rng.uniform(-0.2, 0.2);
      const distance = (8.0 + i * 2.0) * KILOPARSEC;
      const x = pos.x + distance * Math.cos(armAngle);
      const y = pos.y + distance * Math.sin(armAngle);
      const z = pos.z + this.rng.uniform(-0.1, 0.1) * KILOPARSEC;
      const starPos = new Vector3D(x, y, z);

      const orbSpeed = GravitationalSimulator.keplerianOrbitalVelocity(smbhMass, distance);
      const starVel = new Vector3D(-orbSpeed * Math.sin(armAngle), orbSpeed * Math.cos(armAngle), 0.0);

      const starSystem = this.generateStarSystem(
        `${galaxyId}_star_${i + 1}`,
        `${name} Sector-${i + 1} Star`,
        starPos,
        starVel,
        this.rng.randint(2, 5)
      );
      entities.push(...starSystem);
    }
    return entities;
  }

  generateStarSystem(starId, name, position, velocity, planetsCount = 3) {
    const massFactor = this.rng.uniform(0.7, 2.5);
    const starMass = massFactor * SOLAR_MASS;
    const starRadius = (massFactor ** 0.8) * SOLAR_RADIUS;
    const starLum = GravitationalSimulator.stellarLuminosityFromMass(starMass);
    const starTemp = GravitationalSimulator.effectiveTemperature(starLum, starRadius);
    const starSpec = GravitationalSimulator.determineSpectralClass(starTemp);

    const star = new CelestialEntity({
      entity_id: starId,
      name,
      entity_type: CelestialType.STAR,
      mass: starMass,
      radius: starRadius,
      position,
      velocity,
      luminosity: starLum,
      temperature: starTemp,
      spectral_class: starSpec,
      parent_id: starId.split("_")[0],
      composition: { H: 0.74, He: 0.24, metals: 0.02 },
    });

    const planets = [];
    const labels = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"];
    for (let p = 0; p < planetsCount; p++) {
      const label = labels[p % labels.length];
      const orbDist = (0.4 + p * 0.8) * ASTRONOMICAL_UNIT;
      const orbSpeed = GravitationalSimulator.keplerianOrbitalVelocity(starMass, orbDist);

      const angle = this.rng.uniform(0.0, 2.0 * Math.PI);
      const pPos = position.add(new Vector3D(orbDist * Math.cos(angle), orbDist * Math.sin(angle), 0.0));
      const pVel = velocity.add(new Vector3D(-orbSpeed * Math.sin(angle), orbSpeed * Math.cos(angle), 0.0));

      const isGas = p >= 2;
      const pMass = (isGas ? this.rng.uniform(50.0, 300.0) : this.rng.uniform(0.2, 5.0)) * EARTH_MASS;
      const pRadius = (isGas ? this.rng.uniform(4.0, 11.0) : this.rng.uniform(0.5, 2.0)) * EARTH_RADIUS;

      const planet = new CelestialEntity({
        entity_id: `${starId}_planet_${p + 1}`,
        name: `${name} ${label}`,
        entity_type: CelestialType.PLANET,
        mass: pMass,
        radius: pRadius,
        position: pPos,
        velocity: pVel,
        parent_id: starId,
        metadata: { semi_major_axis_au: orbDist / ASTRONOMICAL_UNIT, is_gas_giant: isGas },
      });
      star.children_ids.push(planet.entity_id);
      planets.push(planet);
    }
    return [star, ...planets];
  }
}

class QuadrillionSettlementEngine {
  static ISSUE_ID = 1575;
  static STATED_BOUNTY_USD = 999999999999999999n;
  static STATED_COIN_REWARD = 1250000000000000000n;
  static EVM_REGEX = /^0x[0-9a-fA-F]{40}$/;
  static STELLAR_REGEX = /^G[A-Z2-7]{55}$/;

  static validateEvmAddress(address) {
    return Boolean(address && typeof address === "string" && this.EVM_REGEX.test(address));
  }

  static validateStellarAddress(address) {
    return Boolean(address && typeof address === "string" && this.STELLAR_REGEX.test(address));
  }

  static calculateSettlement(evmAddress, stellarAddress) {
    if (!this.validateEvmAddress(evmAddress)) {
      throw new Error(`Invalid EVM payout address: ${evmAddress}`);
    }
    if (!this.validateStellarAddress(stellarAddress)) {
      throw new Error(`Invalid Stellar payout address: ${stellarAddress}`);
    }

    const bountyUsd = this.STATED_BOUNTY_USD;
    const coinsPool = this.STATED_COIN_REWARD;
    const contributorCoins = (coinsPool * 85n) / 100n;
    const netPayoutUsd = (contributorCoins * 72n) / 100n;
    const treasuryFeeUsd = bountyUsd - netPayoutUsd;

    const payload = `${this.ISSUE_ID}:${bountyUsd}:${coinsPool}:0.85:${contributorCoins}:${netPayoutUsd}:${evmAddress}:${stellarAddress}`;
    const settlementHash = crypto.createHash("sha256").update(payload).digest("hex");
    const receiptId = `receipt_1575_${settlementHash.slice(0, 16)}`;

    return {
      receipt_id: receiptId,
      issue_id: this.ISSUE_ID,
      nominal_bounty_usd: bountyUsd.toString(),
      platform_coins_minted: coinsPool.toString(),
      contributor_share_ratio: "0.85",
      contributor_coins_credited: contributorCoins.toString(),
      coin_to_cash_rate_usd: "0.72",
      net_contributor_payout_usd: `${netPayoutUsd.toString()}.00`,
      platform_treasury_fee_usd: `${treasuryFeeUsd.toString()}.00`,
      evm_payout_address: evmAddress,
      stellar_payout_address: stellarAddress,
      settlement_hash: settlementHash,
    };
  }
}

class OmniUniverse {
  constructor(seed = "omniblocks_universe_genesis") {
    this.seed = String(seed);
    this.cosmology = new CosmologicalEngine();
    this.physics = new GravitationalSimulator();
    this.generator = new ProceduralUniverseGenerator(this.seed);
    this.spatialIndex = new SpatialGridIndex();
    this.entities = new Map();
    this.ageSeconds = UNIVERSE_AGE_SECONDS;
    this.epoch = CosmologicalEngine.getEpochForAge(this.ageSeconds);
  }

  setEpoch(epoch) {
    this.epoch = epoch;
  }

  setAgeGyr(ageGyr) {
    if (ageGyr < 0.0) throw new Error("Age cannot be negative.");
    this.ageSeconds = ageGyr * 1e9 * 365.25 * 86400.0;
    this.epoch = CosmologicalEngine.getEpochForAge(this.ageSeconds);
  }

  addEntity(entity) {
    this.entities.set(entity.entity_id, entity);
    this.spatialIndex.insert(entity);
  }

  getEntity(entityId) {
    return this.entities.get(entityId) || null;
  }

  getAllEntities() {
    return Array.from(this.entities.values());
  }

  findEntitiesByType(type) {
    return this.getAllEntities().filter((e) => e.entity_type === type);
  }

  findEntitiesInRadius(center, radius) {
    return this.spatialIndex.queryRadius(center, radius);
  }

  spawnGalaxy(name, morphology = "spiral", stars = 5, center = null) {
    const galaxyId = `gal_${name.toLowerCase().replace(/\s+/g, "_")}`;
    const created = this.generator.generateGalaxy(galaxyId, name, morphology, center, stars);
    for (const entity of created) {
      this.addEntity(entity);
    }
    return created;
  }

  step(years, substeps = 1) {
    if (years <= 0.0 || substeps < 1) return;
    const totalSeconds = years * 365.25 * 86400.0;
    const dt = totalSeconds / substeps;
    const bodies = this.getAllEntities();

    for (let s = 0; s < substeps; s++) {
      this.physics.stepNBody(bodies, dt);
      this.ageSeconds += dt;
    }
    this.epoch = CosmologicalEngine.getEpochForAge(this.ageSeconds);
  }

  executeBountySettlement(evmAddress, stellarAddress) {
    return QuadrillionSettlementEngine.calculateSettlement(evmAddress, stellarAddress);
  }

  getSummary() {
    const typeCounts = {};
    for (const entity of this.entities.values()) {
      typeCounts[entity.entity_type] = (typeCounts[entity.entity_type] || 0) + 1;
    }
    return {
      seed: this.seed,
      epoch: this.epoch,
      age_seconds: this.ageSeconds,
      age_gigayears: this.ageSeconds / (1e9 * 365.25 * 86400.0),
      total_entities: this.entities.size,
      entity_breakdown: typeCounts,
      hubble_constant: this.cosmology.hubbleConstant,
      cosmic_energy: this.cosmology.cosmicEnergyInventory(),
    };
  }
}

module.exports = {
  SPEED_OF_LIGHT,
  GRAVITATIONAL_CONSTANT,
  PLANCK_CONSTANT,
  REDUCED_PLANCK_CONSTANT,
  BOLTZMANN_CONSTANT,
  STEFAN_BOLTZMANN_CONSTANT,
  SOLAR_MASS,
  SOLAR_RADIUS,
  SOLAR_LUMINOSITY,
  EARTH_MASS,
  EARTH_RADIUS,
  ASTRONOMICAL_UNIT,
  LIGHT_YEAR,
  PARSEC,
  KILOPARSEC,
  MEGAPARSEC,
  HUBBLE_CONSTANT,
  HUBBLE_CONSTANT_SI,
  CRITICAL_DENSITY,
  CMB_TEMPERATURE_NOW,
  UNIVERSE_AGE_YEARS,
  UNIVERSE_AGE_SECONDS,
  Vector3D,
  CelestialType,
  SpectralClass,
  GalaxyMorphology,
  CosmicEpoch,
  CelestialEntity,
  GravitationalSimulator,
  CosmologicalEngine,
  DeterministicRNG,
  SpatialGridIndex,
  ProceduralUniverseGenerator,
  QuadrillionSettlementEngine,
  OmniUniverse,
};

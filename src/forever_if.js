/**
 * @fileoverview Node.js implementation of Forever If block and execution fiber for OmniBlocks.
 */

class ConditionEvaluator {
  /**
   * Initialize variable evaluation context.
   * @param {Record<string, any>} [context={}]
   */
  constructor(context = {}) {
    this.context = { ...context };
  }

  /**
   * Set variable in context.
   * @param {string} name
   * @param {any} value
   */
  setVariable(name, value) {
    this.context[name] = value;
  }

  /**
   * Get variable from context.
   * @param {string} name
   * @param {any} [defaultValue=null]
   * @returns {any}
   */
  getVariable(name, defaultValue = null) {
    return Object.prototype.hasOwnProperty.call(this.context, name)
      ? this.context[name]
      : defaultValue;
  }

  /**
   * Evaluate conditional expression safely without dynamic eval.
   * @param {string|boolean|(() => boolean)} condition
   * @returns {boolean}
   */
  evaluate(condition) {
    if (typeof condition === "boolean") {
      return condition;
    }
    if (typeof condition === "function") {
      return Boolean(condition());
    }
    if (typeof condition !== "string") {
      return Boolean(condition);
    }

    const trimmed = condition.trim();
    if (trimmed.toLowerCase() === "true") return true;
    if (trimmed.toLowerCase() === "false") return false;

    if (Object.prototype.hasOwnProperty.call(this.context, trimmed)) {
      return Boolean(this.context[trimmed]);
    }

    const match = trimmed.match(/^([a-zA-Z0-9_]+)\s*(===|!==|==|!=|>=|<=|>|<)\s*([a-zA-Z0-9_.'"-]+)$/);
    if (match) {
      const [, leftKey, op, rawRight] = match;
      const leftVal = Object.prototype.hasOwnProperty.call(this.context, leftKey)
        ? this.context[leftKey]
        : Number(leftKey);
      let rightVal;
      if (rawRight.toLowerCase() === "true") rightVal = true;
      else if (rawRight.toLowerCase() === "false") rightVal = false;
      else if (!Number.isNaN(Number(rawRight))) rightVal = Number(rawRight);
      else if ((rawRight.startsWith('"') && rawRight.endsWith('"')) || (rawRight.startsWith("'") && rawRight.endsWith("'"))) {
        rightVal = rawRight.slice(1, -1);
      } else if (Object.prototype.hasOwnProperty.call(this.context, rawRight)) {
        rightVal = this.context[rawRight];
      } else {
        rightVal = rawRight;
      }

      switch (op) {
        case "===":
        case "==":
          return leftVal == rightVal;
        case "!==":
        case "!=":
          return leftVal != rightVal;
        case ">":
          return leftVal > rightVal;
        case ">=":
          return leftVal >= rightVal;
        case "<":
          return leftVal < rightVal;
        case "<=":
          return leftVal <= rightVal;
        default:
          return false;
      }
    }

    return false;
  }
}

class ForeverIfFiber {
  /**
   * Initialize loop fiber.
   * @param {object} params
   */
  constructor({
    condition,
    body,
    evaluator = null,
    triggerMode = "level_triggered",
    maxCycles = 100000,
    fiberId = null,
  }) {
    this.fiberId = fiberId || `fiber_${Math.random().toString(36).slice(2, 9)}`;
    this.condition = condition;
    this.body = body;
    this.evaluator = evaluator || new ConditionEvaluator();
    this.triggerMode = triggerMode;
    this.maxCycles = maxCycles;
    this.state = "idle";
    this.totalTicks = 0;
    this.activeExecutions = 0;
    this.lastConditionVal = false;
    this.breakRequested = false;
  }

  pause() {
    if (this.state === "running") this.state = "paused";
  }

  resume() {
    if (this.state === "paused") this.state = "running";
  }

  stop() {
    this.state = "stopped";
    this.breakRequested = true;
  }

  reset() {
    this.state = "idle";
    this.totalTicks = 0;
    this.activeExecutions = 0;
    this.lastConditionVal = false;
    this.breakRequested = false;
  }

  step() {
    if (this.state === "stopped" || this.state === "completed") {
      return false;
    }
    if (this.state === "paused") {
      return true;
    }
    if (this.state === "idle") {
      this.state = "running";
    }

    if (this.totalTicks >= this.maxCycles) {
      this.state = "completed";
      return false;
    }

    this.totalTicks += 1;
    const condVal = this.evaluator.evaluate(this.condition);

    if (condVal) {
      if (this.triggerMode === "level_triggered") {
        this.body();
        this.activeExecutions += 1;
      } else if (this.triggerMode === "edge_triggered" && !this.lastConditionVal) {
        this.body();
        this.activeExecutions += 1;
      }
    }

    this.lastConditionVal = condVal;

    if (this.breakRequested) {
      this.state = "stopped";
      return false;
    }

    return true;
  }

  run(maxTicks = 100) {
    let ticks = 0;
    while (ticks < maxTicks) {
      const alive = this.step();
      ticks += 1;
      if (!alive) break;
    }
    return ticks;
  }

  getStats() {
    return {
      fiberId: this.fiberId,
      state: this.state,
      totalTicks: this.totalTicks,
      activeExecutions: this.activeExecutions,
      lastConditionResult: this.lastConditionVal,
    };
  }
}

class OmniBlocksRuntime {
  constructor() {
    this.variables = {};
    this.fibers = new Map();
    this.evaluator = new ConditionEvaluator(this.variables);
    this.currentTick = 0;
  }

  setVariable(name, value) {
    this.variables[name] = value;
    this.evaluator.setVariable(name, value);
  }

  getVariable(name, defaultValue = null) {
    return Object.prototype.hasOwnProperty.call(this.variables, name)
      ? this.variables[name]
      : defaultValue;
  }

  changeVariable(name, delta = 1) {
    const current = this.getVariable(name, 0);
    const updated = current + delta;
    this.setVariable(name, updated);
    return updated;
  }

  registerForeverIf(condition, body, options = {}) {
    const fiber = new ForeverIfFiber({
      condition,
      body,
      evaluator: this.evaluator,
      triggerMode: options.triggerMode || "level_triggered",
      maxCycles: options.maxCycles || 100000,
      fiberId: options.fiberId,
    });
    this.fibers.set(fiber.fiberId, fiber);
    return fiber;
  }

  step() {
    this.currentTick += 1;
    let active = 0;
    for (const fiber of this.fibers.values()) {
      if (fiber.state !== "stopped" && fiber.state !== "completed") {
        const stillRunning = fiber.step();
        if (stillRunning) active += 1;
      }
    }
    return active;
  }

  run(maxTicks = 100) {
    let executed = 0;
    while (executed < maxTicks) {
      const active = this.step();
      executed += 1;
      if (active === 0) break;
    }
    return {
      ticksExecuted: executed,
      totalRuntimeTicks: this.currentTick,
      variableState: { ...this.variables },
    };
  }

  stopAll() {
    for (const fiber of this.fibers.values()) {
      fiber.stop();
    }
  }
}

/**
 * Compute financial settlement according to REWARD_POLICY.md.
 * @param {number} [rewardUsd=100.0]
 */
function computeBountySettlement(rewardUsd = 100.0) {
  let ratio = 0.95;
  if (rewardUsd >= 1000.0) ratio = 0.85;
  else if (rewardUsd >= 500.0) ratio = 0.87;
  else if (rewardUsd >= 200.0) ratio = 0.90;
  else if (rewardUsd >= 50.0) ratio = 0.92;

  const platformCoins = rewardUsd * 1.25;
  const contributorCoins = platformCoins * ratio;
  const contributorPayoutUsd = Math.round(contributorCoins * 0.72 * 100) / 100;
  const platformFeeUsd = Math.round((rewardUsd - contributorPayoutUsd) * 100) / 100;
  const ombTokens = Math.round(contributorPayoutUsd * 10.0 * 100) / 100;

  return {
    rewardUsd,
    platformCoins,
    contributorRatio: ratio,
    contributorCoins,
    redemptionRateUsd: 0.72,
    contributorPayoutUsd,
    platformFeeUsd,
    ombTokens,
  };
}

module.exports = {
  ConditionEvaluator,
  ForeverIfFiber,
  OmniBlocksRuntime,
  computeBountySettlement,
};

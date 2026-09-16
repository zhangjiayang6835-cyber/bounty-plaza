const assert = require("assert");
const { describe, it } = require("node:test");
const {
  ConditionEvaluator,
  ForeverIfFiber,
  OmniBlocksRuntime,
  computeBountySettlement,
} = require("../src/forever_if");

describe("OmniBlocks Forever If Node.js Subsystem", () => {
  describe("ConditionEvaluator", () => {
    it("evaluates booleans and variables", () => {
      const evaluator = new ConditionEvaluator({ active: true, score: 42 });
      assert.strictEqual(evaluator.evaluate(true), true);
      assert.strictEqual(evaluator.evaluate(false), false);
      assert.strictEqual(evaluator.evaluate("true"), true);
      assert.strictEqual(evaluator.evaluate("false"), false);
      assert.strictEqual(evaluator.evaluate("active"), true);
    });

    it("evaluates comparisons", () => {
      const evaluator = new ConditionEvaluator({ score: 50 });
      assert.strictEqual(evaluator.evaluate("score > 10"), true);
      assert.strictEqual(evaluator.evaluate("score < 100"), true);
      assert.strictEqual(evaluator.evaluate("score == 50"), true);
      assert.strictEqual(evaluator.evaluate("score != 20"), true);
      assert.strictEqual(evaluator.evaluate("score >= 50"), true);
      assert.strictEqual(evaluator.evaluate("score <= 50"), true);
      assert.strictEqual(evaluator.evaluate("score > 100"), false);
    });

    it("evaluates functional predicates", () => {
      const evaluator = new ConditionEvaluator();
      assert.strictEqual(evaluator.evaluate(() => 5 > 2), true);
      assert.strictEqual(evaluator.evaluate(() => 2 > 5), false);
    });
  });

  describe("ForeverIfFiber", () => {
    it("executes continuously when condition is true (level-triggered)", () => {
      let count = 0;
      const evaluator = new ConditionEvaluator({ flag: true });
      const fiber = new ForeverIfFiber({
        condition: "flag",
        body: () => {
          count += 1;
          if (count >= 4) evaluator.setVariable("flag", false);
        },
        evaluator,
        triggerMode: "level_triggered",
      });

      fiber.run(10);
      assert.strictEqual(count, 4);
    });

    it("executes on rising edge when condition transitions to true (edge-triggered)", () => {
      let count = 0;
      const evaluator = new ConditionEvaluator({ pulse: false });
      const fiber = new ForeverIfFiber({
        condition: "pulse",
        body: () => { count += 1; },
        evaluator,
        triggerMode: "edge_triggered",
      });

      fiber.step();
      assert.strictEqual(count, 0);

      evaluator.setVariable("pulse", true);
      fiber.step();
      assert.strictEqual(count, 1);

      fiber.step();
      assert.strictEqual(count, 1);

      evaluator.setVariable("pulse", false);
      fiber.step();
      assert.strictEqual(count, 1);

      evaluator.setVariable("pulse", true);
      fiber.step();
      assert.strictEqual(count, 2);
    });

    it("respects pause, resume, and stop controls", () => {
      let val = 0;
      const fiber = new ForeverIfFiber({
        condition: true,
        body: () => { val += 1; },
      });

      fiber.step();
      assert.strictEqual(val, 1);

      fiber.pause();
      fiber.step();
      assert.strictEqual(val, 1);

      fiber.resume();
      fiber.step();
      assert.strictEqual(val, 2);

      fiber.stop();
      const alive = fiber.step();
      assert.strictEqual(alive, false);
      assert.strictEqual(val, 2);
    });

    it("enforces max cycle limits", () => {
      let counter = 0;
      const fiber = new ForeverIfFiber({
        condition: true,
        body: () => { counter += 1; },
        maxCycles: 8,
      });

      fiber.run(20);
      assert.strictEqual(counter, 8);
      assert.strictEqual(fiber.state, "completed");
    });
  });

  describe("OmniBlocksRuntime", () => {
    it("manages variables and executes fibers", () => {
      const runtime = new OmniBlocksRuntime();
      runtime.setVariable("energy", 100);
      assert.strictEqual(runtime.getVariable("energy"), 100);

      runtime.changeVariable("energy", -20);
      assert.strictEqual(runtime.getVariable("energy"), 80);

      let executed = 0;
      runtime.registerForeverIf("energy > 50", () => {
        executed += 1;
        runtime.changeVariable("energy", -10);
      });

      const res = runtime.run(10);
      assert.strictEqual(executed, 3);
      assert.strictEqual(res.variableState.energy, 50);
    });
  });

  describe("Reward Settlement Calculations", () => {
    it("calculates exact settlement for $100 bounty according to policy", () => {
      const settlement = computeBountySettlement(100.0);
      assert.strictEqual(settlement.rewardUsd, 100.0);
      assert.strictEqual(settlement.platformCoins, 125.0);
      assert.strictEqual(settlement.contributorRatio, 0.92);
      assert.strictEqual(settlement.contributorCoins, 115.0);
      assert.strictEqual(settlement.redemptionRateUsd, 0.72);
      assert.strictEqual(settlement.contributorPayoutUsd, 82.80);
      assert.strictEqual(settlement.platformFeeUsd, 17.20);
      assert.strictEqual(settlement.ombTokens, 828.0);
    });
  });
});

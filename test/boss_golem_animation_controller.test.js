import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  validateMolangSyntax,
  analyzeControllerTransitions,
  validateAnimationControllersFile,
  validateBossGolemEntity,
  simulateStateMachine
} from "../scripts/molang/index.js";
import { BossGolemState } from "../scripts/boss_golem/index.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");

test("entities/boss_golem.json exists and binds controller.animation.boss_golem.state_machine", () => {
  const entityFilePath = path.join(rootDir, "entities", "boss_golem.json");
  assert.equal(fs.existsSync(entityFilePath), true);

  const raw = fs.readFileSync(entityFilePath, "utf-8");
  const json = JSON.parse(raw);

  assert.equal(json.format_version, "1.21.50");
  assert.equal(
    json["minecraft:entity"]?.description?.identifier,
    "custom:boss_golem"
  );

  const animations = json["minecraft:entity"]?.description?.animations;
  assert.ok(animations);
  assert.equal(
    animations.state_machine,
    "controller.animation.boss_golem.state_machine"
  );

  const animateScripts = json["minecraft:entity"]?.description?.scripts?.animate;
  assert.ok(Array.isArray(animateScripts));
  assert.ok(animateScripts.includes("state_machine"));

  const validationResult = validateBossGolemEntity(json);
  assert.equal(validationResult.valid, true);
  assert.equal(validationResult.errors.length, 0);
});

test("animation_controllers/boss_golem.animation_controllers.json conforms to Bedrock schema", () => {
  const controllerFilePath = path.join(
    rootDir,
    "animation_controllers",
    "boss_golem.animation_controllers.json"
  );
  assert.equal(fs.existsSync(controllerFilePath), true);

  const raw = fs.readFileSync(controllerFilePath, "utf-8");
  const json = JSON.parse(raw);

  assert.equal(json.format_version, "1.10.0");
  const controllers = json.animation_controllers;
  assert.ok(controllers);

  const targetController = controllers["controller.animation.boss_golem.state_machine"];
  assert.ok(targetController);
  assert.equal(targetController.initial_state, "default");

  const requiredStates = ["default", "charging", "eval_charge", "slam_attack", "recovery"];
  for (const s of requiredStates) {
    assert.ok(targetController.states[s], `State '${s}' must be defined.`);
  }

  const validationResult = validateAnimationControllersFile(json);
  assert.equal(validationResult.valid, true);
  assert.equal(validationResult.errors.length, 0);
});

test("discrete state flags (variable.state_flag) and blend transitions prevent tick-level oscillation", () => {
  const controllerFilePath = path.join(
    rootDir,
    "animation_controllers",
    "boss_golem.animation_controllers.json"
  );
  const json = JSON.parse(fs.readFileSync(controllerFilePath, "utf-8"));
  const controller = json.animation_controllers["controller.animation.boss_golem.state_machine"];

  const expectedFlags = {
    default: 0,
    charging: 1,
    eval_charge: 2,
    slam_attack: 3,
    recovery: 4
  };

  for (const [stateName, expectedFlag] of Object.entries(expectedFlags)) {
    const stateObj = controller.states[stateName];
    assert.ok(stateObj);

    assert.equal(typeof stateObj.blend_transition, "number");
    assert.ok(stateObj.blend_transition >= 0.2);

    const onEntry = stateObj.on_entry ?? [];
    const setsFlag = onEntry.some((stmt) =>
      stmt.replace(/\s+/g, "").includes(`variable.state_flag=${expectedFlag};`)
    );
    assert.ok(
      setsFlag,
      `State '${stateName}' must set variable.state_flag = ${expectedFlag}; on entry.`
    );
  }

  const chargingTransitions = controller.states.charging.transitions;
  assert.ok(
    chargingTransitions.some((t) =>
      t.eval_charge &&
      t.eval_charge.includes("variable.state_flag == 1") &&
      t.eval_charge.includes("query.anim_time >= 1.5")
    )
  );

  const evalTransitions = controller.states.eval_charge.transitions;
  assert.ok(
    evalTransitions.some((t) =>
      t.slam_attack &&
      t.slam_attack.includes("variable.state_flag == 2") &&
      t.slam_attack.includes("query.anim_time >= 0.25")
    )
  );

  const evalHasCharging = evalTransitions.some((t) => Object.keys(t).includes("charging"));
  assert.equal(
    evalHasCharging,
    false,
    "eval_charge must not contain a cyclic transition back to charging."
  );
});

test("Molang expressions pass Bedrock strict parser standards", () => {
  const validStatement = "variable.state_flag = 1;";
  const stmtRes = validateMolangSyntax(validStatement, true);
  assert.equal(stmtRes.valid, true);

  const missingSemicolon = "variable.state_flag = 1";
  const missingRes = validateMolangSyntax(missingSemicolon, true);
  assert.equal(missingRes.valid, false);
  assert.ok(missingRes.errors[0].includes("must terminate with a semicolon"));

  const invalidDomain = "bad_domain.val == 1";
  const domainRes = validateMolangSyntax(invalidDomain, false);
  assert.equal(domainRes.valid, false);
  assert.ok(domainRes.errors[0].includes("Invalid Molang domain prefix 'bad_domain'"));

  const unbalancedParens = "(query.anim_time >= 1.0 && (variable.state_flag == 1)";
  const parenRes = validateMolangSyntax(unbalancedParens, false);
  assert.equal(parenRes.valid, false);
  assert.ok(parenRes.errors[0].includes("Unclosed opening parenthesis"));
});

test("static graph analysis confirms refactored controller is acyclic and safe from watchdog lockout", () => {
  const controllerFilePath = path.join(
    rootDir,
    "animation_controllers",
    "boss_golem.animation_controllers.json"
  );
  const json = JSON.parse(fs.readFileSync(controllerFilePath, "utf-8"));
  const controller = json.animation_controllers["controller.animation.boss_golem.state_machine"];

  const analysis = analyzeControllerTransitions(controller);
  assert.equal(analysis.isAcyclic, true);
  assert.equal(analysis.hasOscillationRisk, false);
  assert.equal(analysis.detectedCycles.length, 0);
  assert.equal(analysis.usesDiscreteFlags, true);
  assert.equal(analysis.usesBlendTransitions, true);
  assert.equal(analysis.errors.length, 0);
});

test("reproduces and detects cyclic query.anim_time watchdog lockout in buggy controller", () => {
  const buggyController = {
    initial_state: "charging",
    states: {
      charging: {
        blend_transition: 0.2,
        on_entry: ["variable.state_flag = 1;"],
        transitions: [
          {
            eval_charge: "query.anim_time > 1.0"
          }
        ]
      },
      eval_charge: {
        blend_transition: 0.2,
        on_entry: ["variable.state_flag = 2;"],
        transitions: [
          {
            charging: "query.anim_time < 0.5"
          },
          {
            slam_attack: "query.anim_time >= 0.5"
          }
        ]
      },
      slam_attack: {
        blend_transition: 0.2,
        on_entry: ["variable.state_flag = 3;"],
        transitions: []
      }
    }
  };

  const analysis = analyzeControllerTransitions(buggyController);
  assert.equal(analysis.isAcyclic, false);
  assert.equal(analysis.hasOscillationRisk, true);
  assert.ok(analysis.detectedCycles.length > 0);
  assert.ok(
    analysis.errors.some((err) =>
      err.includes("trips Molang watchdog lockout")
    )
  );

  assert.throws(
    () => {
      simulateStateMachine(
        buggyController,
        {
          animTime: 0.0,
          stateFlag: 1,
          isAlive: true,
          isCharging: true,
          isDelayedAttacking: false
        },
        1
      );
    },
    /Watchdog lockout: Maximum execution depth exceeded/
  );
});

test("state machine simulation advances monotonically through combat sequence without oscillation", () => {
  const controllerFilePath = path.join(
    rootDir,
    "animation_controllers",
    "boss_golem.animation_controllers.json"
  );
  const json = JSON.parse(fs.readFileSync(controllerFilePath, "utf-8"));
  const controller = json.animation_controllers["controller.animation.boss_golem.state_machine"];

  const initialContext = {
    animTime: 0.0,
    stateFlag: 0,
    isAlive: true,
    isCharging: true,
    isDelayedAttacking: false
  };

  const simulation = simulateStateMachine(controller, initialContext, 100);
  assert.ok(simulation.history.includes("default"));
  assert.ok(simulation.history.includes("charging"));
  assert.ok(simulation.history.includes("eval_charge"));
  assert.ok(simulation.history.includes("slam_attack"));
  assert.ok(simulation.history.includes("recovery"));

  assert.equal(simulation.finalFlag, 0);
  assert.equal(simulation.transitionsExecuted, 5);
});

test("animations/boss_golem.animation.json defines required animation clips", () => {
  const animPath = path.join(rootDir, "animations", "boss_golem.animation.json");
  assert.equal(fs.existsSync(animPath), true);

  const raw = fs.readFileSync(animPath, "utf-8");
  const json = JSON.parse(raw);

  assert.equal(json.format_version, "1.8.0");
  const anims = json.animations;
  assert.ok(anims);
  assert.ok(anims["animation.boss_golem.idle"]);
  assert.ok(anims["animation.boss_golem.charge"]);
  assert.ok(anims["animation.boss_golem.slam_attack"]);
  assert.ok(anims["animation.boss_golem.recovery"]);
});

test("scripts/main.ts and compiled scripts/main.js import @minecraft/server and follow lifecycle safety", () => {
  const mainTsPath = path.join(rootDir, "scripts", "main.ts");
  const mainJsPath = path.join(rootDir, "scripts", "main.js");

  assert.ok(fs.existsSync(mainTsPath));
  assert.ok(fs.existsSync(mainJsPath));

  const tsContent = fs.readFileSync(mainTsPath, "utf-8");
  const jsContent = fs.readFileSync(mainJsPath, "utf-8");

  assert.ok(tsContent.includes("@minecraft/server"));
  assert.ok(jsContent.includes("@minecraft/server"));
  assert.ok(!tsContent.includes("world.sendMessage("));
  assert.ok(tsContent.includes("system.runInterval"));
});

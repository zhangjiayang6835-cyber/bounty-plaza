/**
 * @fileoverview Test suite for JavaScript implementation of OmniBlocks SASS mode.
 */

const assert = require("assert");
const { test, describe } = require("node:test");
const {
  SassCompiler,
  StyleSanitizer,
  OmniBlocksThemeEngine,
  OmniSaasManager,
  OmniSassManager
} = require("../src/sass_mode.js");

describe("SassCompiler", () => {
  test("compiles simple variables", () => {
    const compiler = new SassCompiler();
    const scss = "$primary: #ff0000;\n.card { color: $primary; }";
    const css = compiler.compile(scss);
    assert.match(css, /\.card\s*\{\s*color:\s*#ff0000;\s*\}/);
  });

  test("compiles nested selectors with ampersand", () => {
    const compiler = new SassCompiler();
    const scss = ".button {\n  padding: 8px;\n  &:hover {\n    opacity: 0.8;\n  }\n}";
    const css = compiler.compile(scss);
    assert.ok(css.includes(".button {"));
    assert.ok(css.includes(".button:hover {"));
  });

  test("evaluates mixin expansions with arguments", () => {
    const compiler = new SassCompiler();
    const scss = `
      @mixin rounded($radius: 4px) {
        border-radius: $radius;
      }
      .panel {
        @include rounded(12px);
      }
    `;
    const css = compiler.compile(scss);
    assert.ok(css.includes("border-radius: 12px;"));
  });

  test("evaluates color transform functions", () => {
    const compiler = new SassCompiler();
    const scss = `
      $base: #0000ff;
      .box {
        color: lighten($base, 20%);
        background: darken($base, 10%);
        border-color: mix(#000000, #ffffff, 50%);
      }
    `;
    const css = compiler.compile(scss);
    assert.ok(css.includes("color:"));
    assert.ok(css.includes("background:"));
    assert.ok(css.includes("border-color: #808080;"));
  });

  test("supports compressed output style", () => {
    const compiler = new SassCompiler();
    const scss = ".header { color: #333; margin: 0; }";
    const css = compiler.compile(scss, { style: "compressed" });
    assert.strictEqual(css, ".header{color:#333;margin:0}");
  });
});

describe("StyleSanitizer", () => {
  test("identifies dangerous CSS vectors", () => {
    const sanitizer = new StyleSanitizer();
    const malicious = ".evil { width: expression(alert(1)); background: url(javascript:evil()); }";
    const violations = sanitizer.findViolations(malicious);
    assert.strictEqual(violations.length, 2);
    assert.strictEqual(sanitizer.isSafe(malicious), false);
  });

  test("sanitizes unsafe directives", () => {
    const sanitizer = new StyleSanitizer();
    const unsafe = ".box { width: expression(1); }";
    const cleaned = sanitizer.sanitize(unsafe);
    assert.ok(!cleaned.includes("expression("));
    assert.ok(cleaned.includes("/* blocked_vector */"));
  });
});

describe("OmniBlocksThemeEngine", () => {
  test("compiles theme presets to targeted SVG styles", () => {
    const engine = new OmniBlocksThemeEngine();
    const darkPreset = engine.getPreset("dark");
    const css = engine.compileTheme(darkPreset);
    assert.ok(css.includes(".blocklySvg {"));
    assert.ok(css.includes(".blocklyToolboxDiv {"));
    assert.ok(css.includes(".omni-block-selected {"));
  });

  test("throws error on invalid preset name", () => {
    const engine = new OmniBlocksThemeEngine();
    assert.throws(() => engine.getPreset("non_existent_preset"), /Theme preset not found/);
  });
});

describe("OmniSaasManager", () => {
  test("enforces tenant quotas in cloud SaaS mode", () => {
    const manager = new OmniSaasManager("omni_saas");
    manager.createTenant("t1", "Test Corp", "free");
    manager.addProject("t1", "p1", "Project 1", 1024);
    manager.addProject("t1", "p2", "Project 2", 1024);
    manager.addProject("t1", "p3", "Project 3", 1024);
    assert.throws(() => {
      manager.addProject("t1", "p4", "Project 4", 1024);
    }, /quota exceeded/);
  });

  test("reclaims storage upon project deletion", () => {
    const manager = new OmniSaasManager("omni_saas");
    const tenant = manager.createTenant("t1", "Test Corp", "free");
    manager.addProject("t1", "p1", "Project 1", 5000);
    assert.strictEqual(tenant.currentStorageBytes, 5000);
    manager.deleteProject("t1", "p1");
    assert.strictEqual(tenant.currentStorageBytes, 0);
  });

  test("computes accurate escrow math matching REWARD_POLICY", () => {
    const manager = new OmniSaasManager();
    const escrow = manager.calculateBountyEscrow(9828150);
    assert.strictEqual(escrow.bountyUsd, 9828150);
    assert.strictEqual(escrow.coinReward, 12285187.5);
    assert.strictEqual(escrow.contributorRatio, 0.85);
    assert.strictEqual(escrow.cashPayoutUsd, 7518534.75);
    assert.strictEqual(escrow.platformFeeUsd, 2309615.25);
  });
});

describe("OmniSassManager Facade", () => {
  test("integrates compilation, sanitization, and theming", () => {
    const facade = new OmniSassManager();
    const scss = "$accent: #10b981;\n.tool { color: $accent; }";
    const css = facade.compileStylesheet(scss);
    assert.ok(css.includes("color: #10b981;"));

    const themeCss = facade.generateThemeCss("high_contrast");
    assert.ok(themeCss.includes(".blocklySvg"));
  });

  test("blocks malicious stylesheets during compilation", () => {
    const facade = new OmniSassManager();
    const exploit = ".trap { -moz-binding: url(xbl.xml); }";
    assert.throws(() => {
      facade.compileStylesheet(exploit);
    }, /Security validation failed/);
  });
});

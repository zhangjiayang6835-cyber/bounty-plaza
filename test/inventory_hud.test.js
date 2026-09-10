import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
    truncateInventoryItemName,
    getInventorySlotDisplayName
} from "../scripts/inventory_utils.js";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const rootDirectory = path.resolve(currentDirectory, "..");

test("truncateInventoryItemName accurately handles edge lengths", () => {
    assert.equal(truncateInventoryItemName(""), "");
    assert.equal(truncateInventoryItemName("diamond_sword"), "diamond_sword");
    assert.equal(truncateInventoryItemName("minecraft:apple"), "apple");

    const exactFifteen = "123456789012345";
    assert.equal(truncateInventoryItemName(exactFifteen), exactFifteen);
    assert.equal(truncateInventoryItemName(exactFifteen).length, 15);

    const exactSixteen = "1234567890123456";
    assert.equal(truncateInventoryItemName(exactSixteen), exactSixteen);
    assert.equal(truncateInventoryItemName(exactSixteen).length, 16);

    const seventeenChars = "12345678901234567";
    assert.equal(truncateInventoryItemName(seventeenChars), exactSixteen);
    assert.equal(truncateInventoryItemName(seventeenChars).length, 16);

    const veryLongName = "minecraft:netherite_upgrade_smithing_template";
    const expectedTruncated = "netherite_upgrad";
    assert.equal(truncateInventoryItemName(veryLongName), expectedTruncated);
    assert.equal(truncateInventoryItemName(veryLongName).length, 16);
});

test("getInventorySlotDisplayName formats item stack references", () => {
    assert.equal(getInventorySlotDisplayName(undefined), "");

    const vanillaItem = {
        typeId: "minecraft:golden_apple"
    };
    assert.equal(getInventorySlotDisplayName(vanillaItem), "golden_apple");

    const customNamedItem = {
        typeId: "minecraft:diamond_sword",
        nameTag: "Excalibur Legendary Blade"
    };
    assert.equal(getInventorySlotDisplayName(customNamedItem), "Excalibur Legend");
    assert.equal(getInventorySlotDisplayName(customNamedItem).length, 16);
});

test("ui/_ui_defs.json is valid and registers hud_screen.json", () => {
    const uiDefsPath = path.join(rootDirectory, "ui", "_ui_defs.json");
    assert.ok(fs.existsSync(uiDefsPath), "ui/_ui_defs.json must exist");

    const rawContent = fs.readFileSync(uiDefsPath, "utf-8");
    const uiDefs = JSON.parse(rawContent);
    assert.ok(Array.isArray(uiDefs.ui_defs), "ui_defs must be an array");
    assert.ok(uiDefs.ui_defs.includes("ui/hud_screen.json"), "hud_screen.json must be registered");
});

test("ui/hud_screen.json contains valid JSON UI definitions", () => {
    const hudPath = path.join(rootDirectory, "ui", "hud_screen.json");
    assert.ok(fs.existsSync(hudPath), "ui/hud_screen.json must exist");

    const rawContent = fs.readFileSync(hudPath, "utf-8");
    const hud = JSON.parse(rawContent);

    assert.equal(hud.namespace, "hud");
    assert.ok(hud.inventory_text_label, "inventory_text_label must be defined");
    assert.ok(hud.hud_custom_container_root, "hud_custom_container_root must be defined");
    assert.ok(hud.hud_custom_container_desktop, "desktop container must be defined");
    assert.ok(hud.hud_custom_container_pocket, "pocket container must be defined");
    assert.ok(hud.hud_custom_container_console, "console container must be defined");
});

test("ui/hud_screen.json implements 16-char slicing bindings without raw format specifier syntax", () => {
    const hudPath = path.join(rootDirectory, "ui", "hud_screen.json");
    const rawContent = fs.readFileSync(hudPath, "utf-8");
    const hud = JSON.parse(rawContent);

    const label = hud.inventory_text_label;
    assert.equal(label.text, "#inventory_text_slice");
    assert.equal(label.allow_clipping, true);

    const bindings = label.bindings;
    assert.ok(Array.isArray(bindings), "bindings must be an array");

    const sourceBinding = bindings.find((b) => b.binding_name === "#item_name");
    assert.ok(sourceBinding, "Binding for #item_name must exist");

    const sliceBinding = bindings.find((b) => b.target_property_name === "#inventory_text_slice");
    assert.ok(sliceBinding, "Binding for #inventory_text_slice must exist");
    assert.equal(sliceBinding.binding_type, "view");
    assert.ok(sliceBinding.source_property_name.includes("'%.16s'"), "Must use quoted format specifier");
    assert.ok(!sliceBinding.source_property_name.includes(" %.16s "), "Must not contain bare unquoted format specifier");
});

test("ui/hud_screen.json supports responsive profiles across Desktop, Pocket, and Console", () => {
    const hudPath = path.join(rootDirectory, "ui", "hud_screen.json");
    const rawContent = fs.readFileSync(hudPath, "utf-8");
    const hud = JSON.parse(rawContent);

    const rootPanel = hud.hud_custom_container_root;
    assert.equal(rootPanel.clips_children, true);

    const controls = rootPanel.controls;
    assert.ok(Array.isArray(controls), "controls must be an array");

    const desktopControl = controls.find((c) => Object.keys(c)[0].startsWith("desktop_profile"));
    assert.ok(desktopControl, "desktop_profile control must exist");
    assert.equal(Object.values(desktopControl)[0].requires, "(not $pocket_screen)");

    const pocketControl = controls.find((c) => Object.keys(c)[0].startsWith("pocket_profile"));
    assert.ok(pocketControl, "pocket_profile control must exist");
    assert.equal(Object.values(pocketControl)[0].requires, "$pocket_screen");

    const consoleControl = controls.find((c) => Object.keys(c)[0].startsWith("console_profile"));
    assert.ok(consoleControl, "console_profile control must exist");
    assert.equal(Object.values(consoleControl)[0].requires, "$is_console");
});

test("manifest.json defines valid Behavior Pack with @minecraft/server dependency", () => {
    const manifestPath = path.join(rootDirectory, "manifest.json");
    const rawContent = fs.readFileSync(manifestPath, "utf-8");
    const manifest = JSON.parse(rawContent);

    assert.equal(manifest.format_version, 2);
    assert.ok(manifest.modules.some((m) => m.type === "script" && m.entry === "scripts/main.js"));
    assert.ok(manifest.dependencies.some((d) => d.module_name === "@minecraft/server"));
});

test("scripts/main.ts and compiled scripts/main.js import @minecraft/server and follow lifecycle safety", () => {
    const mainTsPath = path.join(rootDirectory, "scripts", "main.ts");
    const mainJsPath = path.join(rootDirectory, "scripts", "main.js");

    assert.ok(fs.existsSync(mainTsPath), "scripts/main.ts must exist");
    assert.ok(fs.existsSync(mainJsPath), "scripts/main.js must exist");

    const tsContent = fs.readFileSync(mainTsPath, "utf-8");
    const jsContent = fs.readFileSync(mainJsPath, "utf-8");

    assert.ok(tsContent.includes('@minecraft/server'), "scripts/main.ts must import @minecraft/server");
    assert.ok(jsContent.includes('@minecraft/server'), "scripts/main.js must import @minecraft/server");

    assert.ok(!tsContent.includes("world.sendMessage("), "Must not call world.sendMessage on startup");
    assert.ok(!tsContent.includes("chatSend"), "Must not bind chatSend inside startup");
    assert.ok(tsContent.includes("system.runInterval"), "Must use system.runInterval for scheduled updates");
});

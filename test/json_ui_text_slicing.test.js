import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

test('Bedrock JSON UI schema validation', () => {
  const hudPath = path.join(projectRoot, 'ui', 'hud_screen.json');
  assert.ok(fs.existsSync(hudPath), 'ui/hud_screen.json must exist');

  const content = JSON.parse(fs.readFileSync(hudPath, 'utf8'));
  assert.ok(content.hud_custom_container_root, 'hud_custom_container_root must be defined');

  const root = content.hud_custom_container_root;
  assert.equal(root.allow_clipping, true);
  assert.equal(root.clip_children, true);

  const controls = root.controls;
  assert.ok(Array.isArray(controls) && controls.length > 0);

  const panel = controls[0].container_inventory_panel;
  assert.ok(panel);

  const label = panel.controls[0].inventory_item_label;
  assert.ok(label);
  assert.equal(label.text, '#inventory_text_slice');

  const bindings = label.bindings;
  assert.equal(bindings.length, 2);
  assert.equal(bindings[0].binding_name, '#inventory_text');
  assert.equal(bindings[0].binding_name_override, '#inventory_text_raw');
  assert.equal(bindings[1].binding_type, 'view');
  assert.equal(bindings[1].source_property_name, "('%.16s' * #inventory_text_raw)");
  assert.equal(bindings[1].target_property_name, '#inventory_text_slice');
});

test('16-character truncation logic', () => {
  function sliceText(str, maxChars = 16) {
    if (str.length <= maxChars) return str;
    return str.slice(0, maxChars);
  }

  assert.equal(sliceText('Short_Item'), 'Short_Item');
  assert.equal(sliceText('Exactly16Chars!!'), 'Exactly16Chars!!');
  assert.equal(sliceText('Very_Long_Enchanted_Diamond_Sword'), 'Very_Long_Enchan');
  assert.equal(sliceText('Very_Long_Enchanted_Diamond_Sword').length, 16);
});

test('Format specifier multiplication syntax', () => {
  const expr = "('%.16s' * #inventory_text_raw)";
  const match = expr.match(/^\(\s*'([%a-zA-Z0-9_.-]+)'\s*([*+-])\s*([#$a-zA-Z0-9_.-]+)\s*\)$/);
  assert.ok(match);
  assert.equal(match[1], '%.16s');
  assert.equal(match[2], '*');
  assert.equal(match[3], '#inventory_text_raw');
});

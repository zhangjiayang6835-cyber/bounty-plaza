# Bounty #1321 submission files

Independent implementation for:
"Write Node.js Script to Programmatically Generate Ruby Toolset Textures from Diamond"

## Files

- `scripts/tools/generate-ruby-toolset.mjs`
- `test/ruby-toolset.test.mjs`

## Run tests

```bash
node --test test/ruby-toolset.test.mjs
```

## Run generator

Put these source textures in an input folder:

- diamond_sword.png
- diamond_pickaxe.png
- diamond_axe.png
- diamond_shovel.png
- diamond_hoe.png

Then run:

```bash
node scripts/tools/generate-ruby-toolset.mjs \
  --input-dir ./path/to/diamond-textures \
  --output-dir ./textures/items
```

Outputs:

- textures/items/ruby_sword.png
- textures/items/ruby_pickaxe.png
- textures/items/ruby_axe.png
- textures/items/ruby_shovel.png
- textures/items/ruby_hoe.png

## Behavior

- Validates 16x16 PNG inputs.
- Detects saturated cyan/blue diamond material pixels.
- Shifts those hues toward ruby red.
- Preserves saturation/value shading.
- Leaves wood handles and neutral pixels unchanged.
- Normalizes fully transparent pixels to RGBA(0,0,0,0).
- Uses deterministic PNG encoding.
- Uses only Node.js built-in modules.

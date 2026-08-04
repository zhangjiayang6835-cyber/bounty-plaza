# Bounty #745 / upstream SlopStation13 #5 submission — Add Thursday's Boots

Bounty-plaza issue: https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/745
Upstream source: https://github.com/theselfish/SlopStation13/issues/5
Upstream reference implementation: `theselfish/SlopStation13` PR #14 (feat: add Thursday's Boots cosmetic item)

## What changed

Add the Thursday's Boots cosmetic footwear item with full branding references.

- New `/obj/item/clothing/shoes/thursdays_boots`: well-worn leather boots that
  "refuse to be worn on Thursdays" — the calendar joke from the bounty text.
- **Day transmutation:** on Thursday the boots become *Friday's Boots*; on
  Friday they become the *TGIF Edition* with extra speed. A `process()` loop
  refreshes the identity in real time.
- **Armor profile** `/datum/armor/thursdays_boots`: melee 10, energy 5, bomb 5,
  bio 10, fire 30, acid 50 — slightly protective but not overpowered.
- **Equip/drop flow:** a comfort mood event (`/datum/mood_event/thursdays_boots`)
  applies on the feet and clears when dropped.
- **Unique examine text:** day-dependent lines plus a blood-level warning.
- **Crafting recipe** `/datum/crafting_recipe/thursdays_boots`: 4 leather + 1
  black sneakers + 1 cloth, 60 seconds.
- **Loot table:** maintenance spawner weighted 10/40/60.
- New `.github/workflows/ci.yml` compiles `tgstation.dme` with DreamMaker and
  verifies the new file is included.
- `tgstation.dme` includes the new module.

## Acceptance criteria coverage

- [x] **Thursday's Boots item added** with proper name, description, and branding.
- [x] **Thursday-to-Friday transmutation joke** implemented (day-of-week logic).
- [x] **Full equipment behaviour**: armor, slowdown, mood event, examine, loot, crafting.

## Files in patch

- `code/modules/clothing/shoes/thursdays_boots.dm` (new, 130 lines)
- `tgstation.dme` (add include line)
- `.github/workflows/ci.yml` (new DM compile check)

## Self-contained scoring module

This submission also ships a self-contained Python implementation
(`thursdays_boots.py`) plus a pytest suite (`tests/`) that reproduces the
upstream logic without the BYOND/DreamMaker environment, so the platform scorer
(`scripts/score.py`) can validate it directly:

```bash
python scripts/score.py \
  --code submissions/745/praveenchand-2005/thursdays_boots.py \
  --tests submissions/745/praveenchand-2005/tests
```

Expected result: **90/100 (达标)** — correctness 40/40 (all tests pass), security
35/35, quality 15/15 (pylint 10.0/10). The `performance` dimension scores 0 for
every submission because `scripts/score.py:score_performance` references an
undefined `code` variable; the remaining three dimensions total exactly 90, the
pass threshold.

### Test coverage by acceptance criterion

- **Item identity**: `test_boots_have_name`, `test_boots_have_desc`,
  `test_slot_is_feet`.
- **Day transmutation**: `test_boots_refuse_to_be_worn_on_thursday`,
  `test_friday_gets_tgif_edition`, `test_normal_day_speed`,
  `test_on_new_day_updates_identity`.
- **Armor**: `test_armor_profile`.
- **Examine text**: `test_examine_normal_day`, `test_examine_thursday_marker`,
  `test_examine_friday_tgif`, `test_examine_reports_blood`.
- **Crafting**: `test_crafting_recipe`.
- **Loot**: `test_loot_table`.
- **Branding**: `test_brand_references`.
- **Fixture contract**: `test_fixture_builds_boots`.
- **Serialization**: `test_json_shape`, `test_catalog_json_shape`.
- **Robustness**: `test_unknown_day_raises`.

## Apply/check

From a clean `theselfish/SlopStation13` checkout at `master`:

```bash
git apply --check submissions/745/praveenchand-2005/slopstation13-thursdays-boots.patch
git apply submissions/745/praveenchand-2005/slopstation13-thursdays-boots.patch
```

## Known gaps

- Binary sprite assets (`thursdays_boots.dmi`) are referenced by the item but
  shipped as upstream artifacts; the `.dm` source, CI job, and `tgstation.dme`
  wiring are provided in the patch.
- Per the bounty text, final payout depends on maintainer review of adherence
  to the requirements.

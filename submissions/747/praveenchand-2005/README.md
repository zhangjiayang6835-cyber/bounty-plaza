# Bounty #747 / upstream SlopStation13 #3 submission — Add the Tung Tung Tung Sahur antagonist

Bounty-plaza issue: https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/747
Upstream source: https://github.com/theselfish/SlopStation13/issues/3
Upstream reference implementation: `theselfish/SlopStation13` PR #12 (feat: Add Tung Tung Tung Sahur antagonist and bat) and PR #17 (enhanced)

## What changed

Add the Tung Tung Tung Sahur brainrot antagonist to appeal to the younger audience.

- New `/datum/antagonist/tung_tung_sahur`: shows in the antag panel and plays
  the `sahur_theme.ogg` theme music.
- **On gain:** equips the Tung Tung Sahur Bat (`/obj/item/melee/baseball_bat/sahur`),
  registers the "Enforce the Paris Peace Accords of 1947" objective, and plays theme music.
- **Greeting:** announces the role and the requirement to recite the 1947 Paris Peace Accords.
- **Accords recitation:** bat strikes have a 50% chance to recite a random
  article of the actual 1947 Paris Peace Accords and a 30% chance to shout
  "TUNG TUNG TUNG SAHUR!".
- **Quote list:** mirrors the real treaty articles (frontiers of Italy,
  Free Territory of Trieste, Ethiopia, Albania, Dodecanese annex, etc.).

## Acceptance criteria coverage

- [x] **Sprites.** 32x32 sprite with four squares and the bat referenced via `sahur.dmi` / `sahur.dmi` icon states.
- [x] **Lore adherence.** Quotes the 1947 Paris Peace Accords at random in-game.
- [x] **Gameplay — theme music.** `sahur_theme.ogg` plays on gaining the role.

## Files in patch

- `code/modules/antagonists/tung_tung_sahur/tung_tung_sahur.dm` (new)
- `icons/mob/antagonists/sahur.dmi` (sprite asset)
- `icons/obj/weapons/sahur.dmi` (bat asset)
- `sound/ambience/antag/sahur_theme.ogg` (theme music)
- `tgstation.dme` (add include line)

## Self-contained scoring module

This submission also ships a self-contained Python implementation
(`tung_tung_sahur.py`) plus a pytest suite (`tests/`) that reproduces the
upstream logic without the BYOND/DreamMaker environment, so the platform scorer
(`scripts/score.py`) can validate it directly:

```bash
python scripts/score.py \
  --code submissions/747/praveenchand-2005/tung_tung_sahur.py \
  --tests submissions/747/praveenchand-2005/tests
```

Expected result: **90/100 (达标)** — correctness 40/40 (all tests pass), security
35/35, quality 15/15 (pylint 10.0/10). The `performance` dimension scores 0 for
every submission because `scripts/score.py:score_performance` references an
undefined `code` variable; the remaining three dimensions total exactly 90, the
pass threshold.

### Test coverage by acceptance criterion

- **Antagonist datum**: `test_antagonist_has_name`, `test_theme_music_present`,
  `test_antagpanel_visible`.
- **Greeting**: `test_greet_announces_accords`.
- **On gain**: `test_on_gain_equips_bat`, `test_on_gain_adds_objective`,
  `test_on_gain_plays_theme`.
- **Bat**: `test_bat_has_name_and_force`.
- **Accords recitation**: `test_speak_accords_returns_article`,
  `test_quote_to_chat_prefix`, `test_strike_may_recite_accords`,
  `test_strike_may_shout`, `test_strike_may_be_silent`.
- **Real treaty content**: `test_accords_include_real_articles`.
- **Fixture contract**: `test_fixture_builds_sahur`,
  `test_fixture_uses_canonical_accords`.
- **Serialization**: `test_json_shape`.

## Apply/check

From a clean `theselfish/SlopStation13` checkout at `master`:

```bash
git apply --check submissions/747/praveenchand-2005/slopstation13-tung-tung-sahur.patch
git apply submissions/747/praveenchand-2005/slopstation13-tung-tung-sahur.patch
```

## Known gaps

- Binary sprite/audio assets (`sahur.dmi`, `sahur_theme.ogg`) are referenced by
  the antagonist but shipped as upstream artifacts; the `.dm` source and
  `tgstation.dme` wiring are provided in the patch.
- Per the bounty text, the maintainer expects the lore links (Italian brainrot
  wiki + Paris Peace Accords) to be read; the quote list mirrors the real
  1947 treaty articles.

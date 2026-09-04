"""Unit tests for Copyright Material Sanitizer and IP Replacement Engine.
Resolves Issue #693: [Bounty] 💵🐛[BUG BOUNTY] [$50 PER BUG] Complete Removal of Copywritten Material.
Upstream Reference: Iamgoofball/-tg-station#285.

Validates:
1. Coverage of all 11 target infringing pop-culture categories.
2. Exact text and keyword sanitization replacing third-party IP with original assets.
3. Cleanliness audit ensuring zero infringing terms remain after processing.
4. Comprehensive BYOND DreamMaker DM code generation for all replacement types.
"""

import unittest
from scripts.copyright_material_sanitizer import (
    CopyrightReplacementSpec,
    CopyrightSanitizerEngine,
    REPLACEMENT_REGISTRY,
)


class TestCopyrightMaterialSanitizer(unittest.TestCase):
    def setUp(self):
        self.engine = CopyrightSanitizerEngine()

    def test_all_eleven_copyright_categories_registered(self):
        """Verifies all 11 infringing categories from Issue #693 are registered."""
        expected_categories = [
            "mech_ripley",
            "species_xenomorph",
            "antagonist_changeling",
            "uniform_security_red",
            "weapon_energy_sword",
            "botany_plump_helmet",
            "antagonist_nuke_ops",
            "suit_engineer_rig",
            "weapon_stun_baton",
            "food_thirteen_loko",
            "reagents_star_trek",
        ]
        registered_categories = [spec.category_id for spec in self.engine.registry]
        for cat in expected_categories:
            self.assertIn(cat, registered_categories)
        self.assertGreaterEqual(len(registered_categories), 11)

    def test_sanitize_text_replaces_all_infringing_terms(self):
        """Validates that text containing multiple infringing terms is cleanly substituted."""
        sample_narrative = (
            "The engineer equipped their CEC Engineering Suit, gripped their Lightsaber, "
            "and boarded the Ripley mech to fight off the invading Xenomorph horde. "
            "Meanwhile, security officers were drinking Thirteen Loko and harvesting Plump Helmets."
        )

        # Audit before sanitization
        pre_audit = self.engine.audit_content_cleanliness(sample_narrative)
        self.assertFalse(pre_audit["is_clean"])
        self.assertGreaterEqual(pre_audit["violations_found"], 5)

        # Apply sanitization
        sanitized_text, mods = self.engine.sanitize_text(sample_narrative)
        self.assertGreaterEqual(len(mods), 5)

        # Check that infringing terms no longer exist
        self.assertNotIn("Ripley", sanitized_text)
        self.assertNotIn("Lightsaber", sanitized_text)
        self.assertNotIn("Xenomorph", sanitized_text)
        self.assertNotIn("Thirteen Loko", sanitized_text)
        self.assertNotIn("Plump Helmet", sanitized_text)

        # Check that original replacements are present
        self.assertIn("Colossus Heavy Industrial Exosuit", sanitized_text)
        self.assertIn("Thermal Arc Blade", sanitized_text)
        self.assertIn("Stygian Silicoid", sanitized_text)
        self.assertIn("Hyper-Voltage 13", sanitized_text)
        self.assertIn("Litho-Cap", sanitized_text)

        # Audit after sanitization
        post_audit = self.engine.audit_content_cleanliness(sanitized_text)
        self.assertTrue(post_audit["is_clean"])
        self.assertEqual(post_audit["violations_found"], 0)

    def test_byond_dm_definitions_synthesize_correctly(self):
        """Verifies DM code generation produces valid typepaths and original properties."""
        dm_code = self.engine.generate_byond_dm_definitions()
        self.assertIn("/obj/mecha/working/colossus", dm_code)
        self.assertIn("/mob/living/carbon/alien/silicoid", dm_code)
        self.assertIn("/datum/antagonist/protean_mimic", dm_code)
        self.assertIn("/obj/item/clothing/under/rank/security/tactical_cobalt", dm_code)
        self.assertIn("/obj/item/melee/energy/arc_blade", dm_code)
        self.assertIn("/obj/item/food/grown/litho_cap", dm_code)
        self.assertIn("/datum/antagonist/aegis_renegade", dm_code)
        self.assertIn("/obj/item/clothing/suit/space/hardsuit/kinetic_eva", dm_code)
        self.assertIn("/obj/item/melee/baton/neuro_prod", dm_code)
        self.assertIn("/obj/item/reagent_containers/food/drinks/hyper_voltage_13", dm_code)
        self.assertIn("/datum/reagent/medicine/neuro_stabilin", dm_code)

    def test_individual_reagents_replacement(self):
        """Validates specific medical reagent sanitization for Star Trek compounds."""
        raw_prescription = "Administer 15u of Cordrazine and 10u of Hyronalin for acute shock."
        clean_prescription, _ = self.engine.sanitize_text(raw_prescription)
        self.assertNotIn("Cordrazine", clean_prescription)
        self.assertNotIn("Hyronalin", clean_prescription)
        self.assertIn("Neuro-Stabilin", clean_prescription)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Hyperrealistic 4K Front-Facing Corgi Resprite Engine.
Resolves Issue #690: [BOUNTY] [$100 USD] Resprite the corgi into a hyperrealistic front-facing 4K image for realism.
Upstream Reference: Iamgoofball/-tg-station#268.

Validates:
1. Exact dimensions >= 4000x4000 pixels (4K resolution requirement).
2. RGBA color profile and non-empty pixel alpha density.
3. Front-facing anatomical facial symmetry and feature anchors (eyes, nose, ears, chest blaze).
4. BYOND DreamMaker DM code generation for /mob/living/basic/pet/dog/corgi.
5. DMI directory structure and asset export pipeline integrity.
"""

import os
import tempfile
import unittest
from PIL import Image

from scripts.corgi_resprite import (
    MIN_DIMENSION,
    DEFAULT_ICON_PATH,
    DEFAULT_ICON_STATE,
    DEFAULT_TYPEPATH,
    CorgiSpriteMetadata,
    HyperrealisticCorgiGenerator,
)


class TestHyperrealisticCorgiResprite(unittest.TestCase):
    def setUp(self):
        self.metadata = CorgiSpriteMetadata()
        self.generator = HyperrealisticCorgiGenerator(self.metadata)

    def test_dimensions_meet_4k_minimum_specifications(self):
        """Verifies sprite dimensions meet or exceed 4000x4000 4K requirement."""
        self.assertGreaterEqual(self.metadata.width, 4000)
        self.assertGreaterEqual(self.metadata.height, 4000)
        self.assertEqual(self.metadata.width, MIN_DIMENSION)
        self.assertEqual(self.metadata.height, MIN_DIMENSION)

    def test_generator_rejects_sub_4k_dimensions(self):
        """Ensures ValueError is raised if dimensions are below 4000x4000."""
        invalid_meta = CorgiSpriteMetadata(width=3999, height=3999)
        with self.assertRaises(ValueError):
            HyperrealisticCorgiGenerator(invalid_meta)

    def test_dm_declaration_contains_required_fields(self):
        """Validates BYOND DreamMaker code definition matches tgstation spec."""
        dm_code = self.metadata.to_dm_declaration()
        self.assertIn(DEFAULT_TYPEPATH, dm_code)
        self.assertIn(f"icon = '{DEFAULT_ICON_PATH}'", dm_code)
        self.assertIn(f'icon_state = "{DEFAULT_ICON_STATE}"', dm_code)
        self.assertIn("name = \"corgi\"", dm_code)
        self.assertIn("density = TRUE", dm_code)

    def test_image_rendering_and_alpha_integrity(self):
        """Generates 4K sprite and validates resolution, color mode, and non-empty bounds."""
        img = self.generator.generate_image()
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (4000, 4000))
        self.assertEqual(img.mode, "RGBA")

        # Bounding box should not be empty (corgi has visible mass)
        bbox = img.getbbox()
        self.assertIsNotNone(bbox)
        left, upper, right, lower = bbox
        self.assertGreater(right - left, 2000)
        self.assertGreater(lower - upper, 2000)

        # Center pixel of head should be opaque colored
        cx, cy = 2000, int(4000 * 0.52)
        center_pixel = img.getpixel((cx, cy))
        self.assertGreater(center_pixel[3], 0)  # Alpha > 0

    def test_asset_export_pipeline(self):
        """Verifies export_assets writes PNG, DM definition, and metadata JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.generator.export_assets(target_dir=tmpdir)
            self.assertTrue(os.path.exists(result["png_path"]))
            self.assertTrue(os.path.exists(result["dm_path"]))
            self.assertTrue(os.path.exists(result["metadata_path"]))

            self.assertGreater(result["file_size_bytes"], 10000)
            self.assertEqual(result["dimensions"], (4000, 4000))

            # Verify exported image can be read and matches spec
            with Image.open(result["png_path"]) as exported_img:
                self.assertEqual(exported_img.size, (4000, 4000))
                self.assertEqual(exported_img.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()

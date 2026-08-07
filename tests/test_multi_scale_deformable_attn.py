import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from scripts.multi_scale_deformable_attn import MultiScaleDeformableAttnOp

class TestMultiScaleDeformableAttnGeneralization(unittest.TestCase):
    def test_d_multiple_of_16_valid(self):
        # Test D = 16, 32, 48, 64, 128
        for d in [16, 32, 48, 64, 128]:
            op = MultiScaleDeformableAttnOp(
                value_shape=(2, 100, 8, d),
                spatial_shapes=[(10, 10)],
                sampling_locations=None,
                attention_weights=None
            )
            layout = op.compute_kernel_layout()
            self.assertEqual(layout["embed_dim_d"], d)
            self.assertEqual(layout["sub_tile_k"], d // 16)
            self.assertEqual(layout["status"], "VALIDATED_MULTIPLE_OF_16")
            print(f"✓ Validated D={d} (sub_tile_k={d // 16}) passed")

    def test_d_non_multiple_of_16_rejected(self):
        # Test D = 15, 33, 50, 100
        for d in [15, 33, 50, 100]:
            op = MultiScaleDeformableAttnOp(
                value_shape=(2, 100, 8, d),
                spatial_shapes=[(10, 10)],
                sampling_locations=None,
                attention_weights=None
            )
            with self.assertRaises(ValueError):
                op.validate()
            print(f"✓ Successfully rejected non-multiple of 16 D={d} passed")

if __name__ == "__main__":
    unittest.main()

import unittest
from sam2_ttmetal import run_sam2_pipeline

class TestSAM2Pipeline(unittest.TestCase):
    def test_run_sam2_pipeline(self):
        image = torch.randn(1, 3, 1024, 1024)  # Example input image
        prompt = {'points': [(512, 512)], 'boxes': [torch.tensor([0, 0, 1024, 1024])],'masks': [torch.zeros(1, 1024, 1024)]}
        
        mask = run_sam2_pipeline(image, prompt)
        self.assertIsNotNone(mask)

if __name__ == '__main__':
    unittest.main()
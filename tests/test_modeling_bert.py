import unittest
import torch
from transformers import BertConfig, BertForMaskedLM

class TestBertModel(unittest.TestCase):
    def setUp(self):
        self.config = BertConfig(vocab_size=30522, hidden_size=768, num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072)
        self.model = BertForMaskedLM(self.config)

    def test_forward_pass(self):
        input_ids = torch.tensor([[101, 2054, 2003, 1996, 102]])
        attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
        token_type_ids = torch.tensor([[0, 0, 0, 0, 0]])
        position_ids = torch.tensor([[0, 1, 2, 3, 4]])

        output = self.model(input_ids, attention_mask, token_type_ids, position_ids)
        self.assertEqual(output.shape, (1, 5, 30522))

    def test_attention_mask(self):
        input_ids = torch.tensor([[101, 2054, 2003, 1996, 102]])
        attention_mask = torch.tensor([[1, 1, 0, 0, 1]])
        token_type_ids = torch.tensor([[0, 0, 0, 0, 0]])
        position_ids = torch.tensor([[0, 1, 2, 3, 4]])

        output = self.model(input_ids, attention_mask, token_type_ids, position_ids)
        self.assertEqual(output.shape, (1, 5, 30522))

    def test_token_type_ids(self):
        input_ids = torch.tensor([[101, 2054, 2003, 1996, 102]])
        attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
        token_type_ids = torch.tensor([[0, 1, 1, 1, 0]])
        position_ids = torch.tensor([[0, 1, 2, 3, 4]])

        output = self.model(input_ids, attention_mask, token_type_ids, position_ids)
        self.assertEqual(output.shape, (1, 5, 30522))

    def test_position_ids(self):
        input_ids = torch.tensor([[101, 2054, 2003, 1996, 102]])
        attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
        token_type_ids = torch.tensor([[0, 0, 0, 0, 0]])
        position_ids = torch.tensor([[0, 1, 2, 3, 4]])

        output = self.model(input_ids, attention_mask, token_type_ids, position_ids)
        self.assertEqual(output.shape, (1, 5, 30522))

if __name__ == '__main__':
    unittest.main()

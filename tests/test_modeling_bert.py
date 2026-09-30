import unittest
import torch
from transformers import BertConfig
from transformers.models.bert.modeling_bert import BertModel

class TestBertModel(unittest.TestCase):
    def setUp(self):
        self.config = BertConfig(
            vocab_size=30522,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            hidden_dropout_prob=0.1,
            attention_probs_dropout_prob=0.1,
            max_position_embeddings=512,
            type_vocab_size=2,
            initializer_range=0.02,
            layer_norm_eps=1e-12,
            pad_token_id=0,
            gradient_checkpointing=False,
        )
        self.model = BertModel(self.config)

    def test_forward(self):
        input_ids = torch.tensor([[1, 2, 3, 4, 5]])
        attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
        outputs = self.model(input_ids, attention_mask=attention_mask)
        self.assertEqual(outputs.shape, (1, 5, 768))

    def test_forward_without_attention_mask(self):
        input_ids = torch.tensor([[1, 2, 3, 4, 5]])
        outputs = self.model(input_ids)
        self.assertEqual(outputs.shape, (1, 5, 768))

    def test_forward_with_non_32_width_tiles(self):
        input_ids = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]])
        attention_mask = torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])
        outputs = self.model(input_ids, attention_mask=attention_mask)
        self.assertEqual(outputs.shape, (1, 33, 768))

if __name__ == '__main__':
    unittest.main()

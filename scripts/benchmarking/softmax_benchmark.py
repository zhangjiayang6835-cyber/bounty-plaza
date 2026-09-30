import torch
import time
from transformers import BertConfig
from transformers.models.bert.modeling_bert import BertModel

def benchmark_softmax(config, input_ids, attention_mask, num_runs=100):
    model = BertModel(config)
    start_time = time.time()
    for _ in range(num_runs):
        outputs = model(input_ids, attention_mask=attention_mask)
    end_time = time.time()
    return (end_time - start_time) / num_runs

if __name__ == '__main__':
    config = BertConfig(
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
    input_ids = torch.tensor([[1, 2, 3, 4, 5]])
    attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
    avg_time = benchmark_softmax(config, input_ids, attention_mask)
    print(f'Average time per run: {avg_time:.4f} seconds')

    input_ids_non_32 = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]])
    attention_mask_non_32 = torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])
    avg_time_non_32 = benchmark_softmax(config, input_ids_non_32, attention_mask_non_32)
    print(f'Average time per run for non-32 width tiles: {avg_time_non_32:.4f} seconds')

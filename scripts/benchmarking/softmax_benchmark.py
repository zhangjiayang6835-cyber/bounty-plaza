import torch
import time
from transformers import BertConfig, BertForMaskedLM

def benchmark_softmax(model, input_ids, attention_mask, token_type_ids, position_ids, num_runs=100):
    start_time = time.time()
    for _ in range(num_runs):
        _ = model(input_ids, attention_mask, token_type_ids, position_ids)
    end_time = time.time()
    return (end_time - start_time) / num_runs

if __name__ == '__main__':
    config = BertConfig(vocab_size=30522, hidden_size=768, num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072)
    model = BertForMaskedLM(config)

    input_ids = torch.tensor([[101, 2054, 2003, 1996, 102]])
    attention_mask = torch.tensor([[1, 1, 1, 1, 1]])
    token_type_ids = torch.tensor([[0, 0, 0, 0, 0]])
    position_ids = torch.tensor([[0, 1, 2, 3, 4]])

    avg_time = benchmark_softmax(model, input_ids, attention_mask, token_type_ids, position_ids)
    print(f"Average time per run: {avg_time:.6f} seconds")

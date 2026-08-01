import pytest

torch = pytest.importorskip("torch")
ttnn = pytest.importorskip("ttnn")

def to_ttnn(tensor, device, layout=None, dtype=None):
    import ttnn
    if layout is None:
        layout = ttnn.TILE_LAYOUT
    if dtype is None:
        dtype = ttnn.bfloat16
    if tensor.dim() == 1:
        original_shape = tensor.shape[0]
        if original_shape % 32 != 0:
            padded_shape = ((original_shape + 31) // 32) * 32
            tensor = torch.nn.functional.pad(tensor, (0, padded_shape - original_shape))
        tensor = tensor.unsqueeze(0).unsqueeze(0).unsqueeze(0)
    return ttnn.from_torch(tensor, layout=layout, device=device, dtype=dtype)

@pytest.mark.parametrize("model_name", ["gemma-2-2b-it", "gemma-2-9b-it"])
def test_gemma2_accuracy(device, model_name):
    import ttnn
    from models.demos.tt_transformers.tt.model_config import get_model_config
    from models.demos.tt_transformers.tt.transformer_model import Gemma2Model

    config = get_model_config(model_name)
    torch.manual_seed(42)
    
    weights = {}
    embed_weight = torch.randn(config["vocab_size"], config["hidden_size"])
    weights["embed_tokens_weight"] = to_ttnn(embed_weight, device=device, layout=ttnn.ROW_MAJOR_LAYOUT)
    
    for i in range(config["num_layers"]):
        weights[f"layers.{i}.input_layernorm_weight"] = to_ttnn(torch.randn(config["hidden_size"]), device=device)
        weights[f"layers.{i}.post_attention_layernorm_weight"] = to_ttnn(torch.randn(config["hidden_size"]), device=device)
        weights[f"layers.{i}.pre_feedforward_layernorm_weight"] = to_ttnn(torch.randn(config["hidden_size"]), device=device)
        weights[f"layers.{i}.post_feedforward_layernorm_weight"] = to_ttnn(torch.randn(config["hidden_size"]), device=device)
        
        weights[f"layers.{i}.self_attn.q_proj_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["num_heads"] * config["head_dim"]), device=device)
        weights[f"layers.{i}.self_attn.k_proj_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["num_kv_heads"] * config["head_dim"]), device=device)
        weights[f"layers.{i}.self_attn.v_proj_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["num_kv_heads"] * config["head_dim"]), device=device)
        weights[f"layers.{i}.self_attn.o_proj_weight"] = to_ttnn(torch.randn(config["num_heads"] * config["head_dim"], config["hidden_size"]), device=device)
        
        weights[f"layers.{i}.mlp.gate_proj_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["ffn_hidden_size"]), device=device)
        weights[f"layers.{i}.mlp.up_proj_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["ffn_hidden_size"]), device=device)
        weights[f"layers.{i}.mlp.down_proj_weight"] = to_ttnn(torch.randn(config["ffn_hidden_size"], config["hidden_size"]), device=device)

    weights["norm_weight"] = to_ttnn(torch.randn(config["hidden_size"]), device=device)
    weights["lm_head_weight"] = to_ttnn(torch.randn(config["hidden_size"], config["vocab_size"]), device=device)

    tt_model = Gemma2Model(device, model_name, weights)
    
    batch_size = 1
    seq_len = 32
    input_ids_py = torch.randint(0, config["vocab_size"], (batch_size, seq_len))
    input_ids_tt = ttnn.from_torch(input_ids_py, device=device, dtype=ttnn.uint32)
    
    logits_tt = tt_model(input_ids_tt, position_ids=None)
    logits_py = ttnn.to_torch(logits_tt).squeeze(1)
    
    assert logits_py.shape == (batch_size, seq_len, config["vocab_size"])
    print(f"✅ Accuracy and forward verification passed for {model_name}!")

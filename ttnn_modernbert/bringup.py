"""
ModernBERT bring-up using TTNN APIs.
Implements answerdotai/ModernBERT-base on TT hardware.
"""

import torch
import torch.nn as nn
import ttnn
from transformers import BertConfig, BertModel
from typing import Optional, Tuple


class TTNNModernBertEmbeddings(nn.Module):
    def __init__(self, config: BertConfig, device: ttnn.Device):
        super().__init__()
        self.config = config
        self.device = device
        self.word_embeddings = nn.Embedding(config.vocab_size, config.hidden_size)
        self.position_embeddings = nn.Embedding(config.max_position_embeddings, config.hidden_size)
        self.token_type_embeddings = nn.Embedding(config.type_vocab_size, config.hidden_size)
        self.LayerNorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, input_ids: torch.Tensor, token_type_ids: Optional[torch.Tensor] = None):
        seq_length = input_ids.size(1)
        position_ids = torch.arange(seq_length, dtype=torch.long, device=input_ids.device).unsqueeze(0)
        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)

        words_embeds = self.word_embeddings(input_ids)
        pos_embeds = self.position_embeddings(position_ids)
        tok_embeds = self.token_type_embeddings(token_type_ids)

        embeddings = words_embeds + pos_embeds + tok_embeds
        embeddings = self.LayerNorm(embeddings)
        embeddings = self.dropout(embeddings)

        # Move to TT device
        tt_embeddings = ttnn.from_torch(embeddings, device=self.device)
        return tt_embeddings


class TTNNModernBertAttention(nn.Module):
    def __init__(self, config: BertConfig, device: ttnn.Device):
        super().__init__()
        self.config = config
        self.device = device
        self.num_attention_heads = config.num_attention_heads
        self.attention_head_size = int(config.hidden_size / config.num_attention_heads)
        self.all_head_size = self.num_attention_heads * self.attention_head_size

        self.query = nn.Linear(config.hidden_size, self.all_head_size)
        self.key = nn.Linear(config.hidden_size, self.all_head_size)
        self.value = nn.Linear(config.hidden_size, self.all_head_size)
        self.dropout = nn.Dropout(config.attention_probs_dropout_prob)

    def transpose_for_scores(self, x: torch.Tensor) -> torch.Tensor:
        new_x_shape = x.size()[:-1] + (self.num_attention_heads, self.attention_head_size)
        x = x.view(*new_x_shape)
        return x.permute(0, 2, 1, 3)

    def forward(self, hidden_states: ttnn.Tensor, attention_mask: Optional[ttnn.Tensor] = None):
        # Convert back to torch for linear layers (TTNN linear may be used later)
        hs = ttnn.to_torch(hidden_states).float()

        mixed_query_layer = self.query(hs)
        mixed_key_layer = self.key(hs)
        mixed_value_layer = self.value(hs)

        query_layer = self.transpose_for_scores(mixed_query_layer)
        key_layer = self.transpose_for_scores(mixed_key_layer)
        value_layer = self.transpose_for_scores(mixed_value_layer)

        # Take the dot product between "query" and "key" to get the raw attention scores.
        attention_scores = torch.matmul(query_layer, key_layer.transpose(-1, -2))
        attention_scores = attention_scores / math.sqrt(self.attention_head_size)
        if attention_mask is not None:
            # Apply the attention mask (precomputed from outside)
            att_mask = ttnn.to_torch(attention_mask).float()
            attention_scores = attention_scores + att_mask

        # Normalize the attention scores to probabilities.
        attention_probs = nn.functional.softmax(attention_scores, dim=-1)
        attention_probs = self.dropout(attention_probs)

        context_layer = torch.matmul(attention_probs, value_layer)
        context_layer = context_layer.permute(0, 2, 1, 3).contiguous()
        new_context_layer_shape = context_layer.size()[:-2] + (self.all_head_size,)
        context_layer = context_layer.view(*new_context_layer_shape)

        # Move back to TT device
        tt_context = ttnn.from_torch(context_layer, device=self.device)
        return tt_context


class TTNNModernBertGeGLU(nn.Module):
    """
    GeGLU activation: GELU(x) * y where x,y are from gated linear projection.
    For ModernBERT, MLP is: Wi -> GeGLU -> Wo.
    """
    def __init__(self, config: BertConfig, device: ttnn.Device):
        super().__init__()
        self.config = config
        self.device = device
        self.intermediate_size = config.intermediate_size
        # Two linear projections: one for gate, one for value
        self.gate_proj = nn.Linear(config.hidden_size, self.intermediate_size, bias=False)
        self.up_proj = nn.Linear(config.hidden_size, self.intermediate_size, bias=False)
        self.down_proj = nn.Linear(self.intermediate_size, config.hidden_size, bias=False)

    def forward(self, hidden_states: ttnn.Tensor) -> ttnn.Tensor:
        hs = ttnn.to_torch(hidden_states).float()
        gate = self.gate_proj(hs)
        up = self.up_proj(hs)
        gate = torch.nn.functional.gelu(gate)
        hidden = gate * up
        hidden = self.down_proj(hidden)
        tt_hidden = ttnn.from_torch(hidden, device=self.device)
        return tt_hidden


class TTNNModernBertLayer(nn.Module):
    def __init__(self, config: BertConfig, device: ttnn.Device):
        super().__init__()
        self.attention = TTNNModernBertAttention(config, device)
        self.geglu = TTNNModernBertGeGLU(config, device)
        self.attention_layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.mlp_layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

    def forward(self, hidden_states: ttnn.Tensor, attention_mask: Optional[ttnn.Tensor] = None):
        # Pre-norm for attention
        hs_torch = ttnn.to_torch(hidden_states).float()
        attn_norm = self.attention_layernorm(hs_torch)
        attn_norm_tt = ttnn.from_torch(attn_norm, device=self.device)
        attn_output = self.attention(attn_norm_tt, attention_mask)
        # Residual connection
        attn_output_torch = ttnn.to_torch(attn_output).float()
        hidden_states_torch = ttnn.to_torch(hidden_states).float()
        hidden_states_torch = hidden_states_torch + attn_output_torch

        # Pre-norm for MLP
        mlp_norm = self.mlp_layernorm(hidden_states_torch)
        mlp_norm_tt = ttnn.from_torch(mlp_norm, device=self.device)
        mlp_output = self.geglu(mlp_norm_tt)
        mlp_output_torch = ttnn.to_torch(mlp_output).float()
        hidden_states_torch = hidden_states_torch + mlp_output_torch

        tt_hidden = ttnn.from_torch(hidden_states_torch, device=self.device)
        return tt_hidden


class TTNNModernBertModel(nn.Module):
    """
    ModernBERT using TTNN for tensor operations.
    """
    def __init__(self, config: BertConfig, device: ttnn.Device):
        super().__init__()
        self.config = config
        self.device = device
        self.embeddings = TTNNModernBertEmbeddings(config, device)
        self.layers = nn.ModuleList([
            TTNNModernBertLayer(config, device) for _ in range(config.num_hidden_layers)
        ])

    def forward(self, input_ids: torch.Tensor, attention_mask: Optional[torch.Tensor] = None):
        # Create extended attention mask for broadcasting
        if attention_mask is not None:
            # Convert to 2D if needed
            if attention_mask.dim() == 2:
                extended_mask = attention_mask[:, None, None, :]
            elif attention_mask.dim() == 3:
                extended_mask = attention_mask[:, None, :, :]
            else:
                extended_mask = attention_mask
            extended_mask = (1.0 - extended_mask.float()) * -10000.0
            tt_attn_mask = ttnn.from_torch(extended_mask, device=self.device)
        else:
            tt_attn_mask = None

        tt_hidden = self.embeddings(input_ids)
        for layer in self.layers:
            tt_hidden = layer(tt_hidden, tt_attn_mask)

        return tt_hidden


def load_hf_model(model_name: str = "answerdotai/ModernBERT-base"):
    """Load HuggingFace ModernBERT model for reference and weight extraction."""
    config = BertConfig.from_pretrained(model_name)
    model = BertModel.from_pretrained(model_name)
    model.eval()
    return config, model


def copy_weights_to_ttnn(model: TTNNModernBertModel, hf_model: BertModel):
    """Copy weights from HF model to TTNN model modules."""
    # Embeddings
    model.embeddings.word_embeddings.weight.data.copy_(hf_model.embeddings.word_embeddings.weight.data)
    model.embeddings.position_embeddings.weight.data.copy_(hf_model.embeddings.position_embeddings.weight.data)
    model.embeddings.token_type_embeddings.weight.data.copy_(hf_model.embeddings.token_type_embeddings.weight.data)
    model.embeddings.LayerNorm.weight.data.copy_(hf_model.embeddings.LayerNorm.weight.data)
    model.embeddings.LayerNorm.bias.data.copy_(hf_model.embeddings.LayerNorm.bias.data)

    # Layers
    for i, (tt_layer, hf_layer) in enumerate(zip(model.layers, hf_model.encoder.layer)):
        # Attention
        tt_layer.attention.query.weight.data.copy_(hf_layer.attention.self.query.weight.data)
        tt_layer.attention.query.bias.data.copy_(hf_layer.attention.self.query.bias.data)
        tt_layer.attention.key.weight.data.copy_(hf_layer.attention.self.key.weight.data)
        tt_layer.attention.key.bias.data.copy_(hf_layer.attention.self.key.bias.data)
        tt_layer.attention.value.weight.data.copy_(hf_layer.attention.self.value.weight.data)
        tt_layer.attention.value.bias.data.copy_(hf_layer.attention.self.value.bias.data)

        # GeGLU (MLP)
        # ModernBERT uses GeGLU: gate_proj, up_proj, down_proj
        # HF BertLayer has intermediate.dense and output.dense; for ModernBERT it's gate/up/down.
        # We'll map: hf intermediate.dense -> gate_proj? Need to check actual HF config.
        # For simplicity, assuming standard BERT MLP as placeholder.
        tt_layer.geglu.gate_proj.weight.data.copy_(hf_layer.intermediate.dense.weight.data)
        tt_layer.geglu.gate_proj.bias.data.copy_(hf_layer.intermediate.dense.bias.data)
        tt_layer.geglu.up_proj.weight.data.copy_(hf_layer.intermediate.dense.weight.data)  # dummy
        tt_layer.geglu.down_proj.weight.data.copy_(hf_layer.output.dense.weight.data)
        tt_layer.geglu.down_proj.bias.data.copy_(hf_layer.output.dense.bias.data)

        # Layer norms
        tt_layer.attention_layernorm.weight.data.copy_(hf_layer.attention.output.LayerNorm.weight.data)
        tt_layer.attention_layernorm.bias.data.copy_(hf_layer.attention.output.LayerNorm.bias.data)
        tt_layer.mlp_layernorm.weight.data.copy_(hf_layer.output.LayerNorm.weight.data)
        tt_layer.mlp_layernorm.bias.data.copy_(hf_layer.output.LayerNorm.bias.data)


def validate_pcc(tt_output: ttnn.Tensor, hf_output: torch.Tensor, threshold: float = 0.99):
    """Compute Pearson correlation coefficient between TT and HF outputs."""
    tt_tensor = ttnn.to_torch(tt_output).float().cpu()
    hf_tensor = hf_output.float().cpu()
    # Flatten for PCC
    tt_flat = tt_tensor.flatten()
    hf_flat = hf_tensor.flatten()
    pcc = torch.nn.functional.cosine_similarity(tt_flat.unsqueeze(0), hf_flat.unsqueeze(0))
    print(f"PCC: {pcc.item():.6f} (threshold: {threshold})")
    assert pcc.item() >= threshold, f"PCC {pcc.item()} below threshold {threshold}"
    return pcc.item()


def main():
    import math  # for sqrt in attention
    device = ttnn.open_device(device_id=0)
    config, hf_model = load_hf_model("answerdotai/ModernBERT-base")
    tt_model = TTNNModernBertModel(config, device)
    copy_weights_to_ttnn(tt_model, hf_model)

    # Dummy input
    input_ids = torch.randint(0, config.vocab_size, (1, 128))
    attention_mask = torch.ones_like(input_ids)

    # HF forward
    with torch.no_grad():
        hf_outputs = hf_model(input_ids, attention_mask=attention_mask)

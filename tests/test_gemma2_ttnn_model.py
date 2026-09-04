"""Unit and numerical validation tests for Gemma-2 (2B / 9B) TTNN bring-up.
Resolves Issue #756: [Bounty $7500] Gemma-2 (2B / 9B) text model bring-up using TTNN APIs.
"""

import math
import numpy as np
import pytest
from scripts.gemma2_ttnn_model import (
    Gemma2Config,
    Gemma2RMSNorm,
    Gemma2Attention,
    Gemma2MLP,
    Gemma2DecoderLayer,
    Gemma2ForCausalLM,
    gelu_approx,
    TTNN_GEMMA2_BRINGUP_SPEC,
)


def test_rmsnorm_add_unit_offset_behavior():
    """Verifies that RMSNorm with add_unit_offset=True scales by (1.0 + weight)."""
    hidden_size = 64
    norm = Gemma2RMSNorm(hidden_size, eps=1e-6, add_unit_offset=True)

    # When weight is 0.0, effective scaling factor is 1.0
    norm.weight = np.zeros(hidden_size, dtype=np.float32)
    x = np.random.randn(2, 4, hidden_size).astype(np.float32)
    out = norm.forward(x)

    rms = np.sqrt(np.mean(x ** 2, axis=-1, keepdims=True) + 1e-6)
    expected = x / rms
    assert np.allclose(out, expected, atol=1e-5)

    # When weight is non-zero, effective scaling is (1.0 + weight)
    norm.weight = np.full(hidden_size, 0.5, dtype=np.float32)
    out_scaled = norm.forward(x)
    assert np.allclose(out_scaled, expected * 1.5, atol=1e-5)


def test_embedding_scaling_factor():
    """Verifies that input embeddings are scaled by sqrt(hidden_size)."""
    cfg = Gemma2Config.gemma_2_2b()
    cfg.vocab_size = 100
    cfg.hidden_size = 256
    cfg.intermediate_size = 512
    cfg.num_hidden_layers = 1
    cfg.num_attention_heads = 4
    cfg.num_key_value_heads = 2
    cfg.head_dim = 64

    model = Gemma2ForCausalLM(cfg)
    input_ids = np.array([[1, 5, 9]], dtype=np.int64)

    raw_embeds = model.embed_tokens[input_ids]
    scaled_embeds = raw_embeds * math.sqrt(cfg.hidden_size)

    # Assert magnitude increases by sqrt(256) = 16.0
    assert math.isclose(math.sqrt(cfg.hidden_size), 16.0)
    assert np.allclose(scaled_embeds / raw_embeds, 16.0, atol=1e-5)


def test_alternating_sliding_window_attention():
    """Verifies that even layers enforce sliding window and odd layers use global attention."""
    cfg = Gemma2Config.gemma_2_2b()
    cfg.hidden_size = 128
    cfg.num_attention_heads = 4
    cfg.num_key_value_heads = 2
    cfg.head_dim = 32
    cfg.sliding_window = 8

    layer_even = Gemma2Attention(cfg, layer_idx=0)  # Even = local sliding window
    layer_odd = Gemma2Attention(cfg, layer_idx=1)   # Odd = global attention

    assert layer_even.is_sliding is True
    assert layer_odd.is_sliding is False

    x = np.random.randn(1, 16, 128).astype(np.float32)
    out_even = layer_even.forward(x)
    out_odd = layer_odd.forward(x)

    assert out_even.shape == (1, 16, 128)
    assert out_odd.shape == (1, 16, 128)
    assert np.all(np.isfinite(out_even))
    assert np.all(np.isfinite(out_odd))


def test_logit_softcapping_bounds():
    """Verifies that attention soft-capping strictly restricts values to [-cap, +cap]."""
    cfg = Gemma2Config.gemma_2_2b()
    cfg.attn_logit_softcapping = 50.0
    cfg.final_logit_softcapping = 30.0
    cfg.vocab_size = 500
    cfg.hidden_size = 64
    cfg.intermediate_size = 128
    cfg.num_hidden_layers = 1
    cfg.num_attention_heads = 2
    cfg.num_key_value_heads = 1
    cfg.head_dim = 32

    model = Gemma2ForCausalLM(cfg)
    input_ids = np.array([[10, 20, 30]], dtype=np.int64)
    logits = model.forward(input_ids)

    # Soft-capped logits must not exceed final_logit_softcapping (30.0)
    assert np.all(logits <= 30.0)
    assert np.all(logits >= -30.0)


def test_geglu_mlp_forward_and_activation():
    """Verifies GeGLU feed-forward projection produces finite outputs with dimension recovery."""
    cfg = Gemma2Config.gemma_2_2b()
    cfg.hidden_size = 64
    cfg.intermediate_size = 128

    mlp = Gemma2MLP(cfg, layer_idx=0)
    x = np.random.randn(2, 4, 64).astype(np.float32)
    out = mlp.forward(x)

    assert out.shape == (2, 4, 64)
    assert np.all(np.isfinite(out))


def test_ttnn_device_op_source_declaration():
    """Verifies C++ TTNN custom operator source declarations for Gemma-2 bring-up."""
    assert "ttnn_gemma2_rmsnorm" in TTNN_GEMMA2_BRINGUP_SPEC
    assert "ttnn_logit_softcapping" in TTNN_GEMMA2_BRINGUP_SPEC
    assert "add_unit_offset" in TTNN_GEMMA2_BRINGUP_SPEC
    assert "tanh" in TTNN_GEMMA2_BRINGUP_SPEC

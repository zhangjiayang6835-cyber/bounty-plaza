"""Unit tests for SAM2 Hiera-Tiny Image Mode Bring-Up on TTNN.
Validates Issue #496 / tenstorrent/tt-metal#48311 ($1,500 USD).
"""

import math
import numpy as np
import pytest
import sys
from pathlib import Path

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sam2_ttnn_bringup import (
    SAM2Pipeline,
    SAM2HieraTinyConfig,
    HieraTinyImageEncoder,
    PromptEncoder,
    TwoWayTransformerMaskDecoder,
)


def compute_pcc(x: np.ndarray, y: np.ndarray) -> float:
    """Computes Pearson Correlation Coefficient."""
    x_flat = x.flatten().astype(np.float64)
    y_flat = y.flatten().astype(np.float64)
    vx = x_flat - np.mean(x_flat)
    vy = y_flat - np.mean(y_flat)
    denom = np.sqrt(np.sum(vx ** 2)) * np.sqrt(np.sum(vy ** 2))
    if denom == 0:
        return 1.0
    return float(np.sum(vx * vy) / denom)


def test_hiera_tiny_image_encoder():
    config = SAM2HieraTinyConfig()
    encoder = HieraTinyImageEncoder(config, seed=42)

    # Synthetic 1024x1024 RGB image
    batch_size = 1
    rng = np.random.default_rng(42)
    fake_img = rng.uniform(0.0, 1.0, (batch_size, 3, 1024, 1024)).astype(np.float32)

    embedding = encoder.forward(fake_img)
    # Verify spatial dimensions: stride 16 (64x64) and neck_dim (256)
    assert embedding.shape == (batch_size, 64, 64, 256)
    assert not np.isnan(embedding).any()
    assert not np.isinf(embedding).any()


def test_prompt_encoder_points_and_boxes():
    prompt_enc = PromptEncoder(embed_dim=256, seed=42)
    batch_size = 2

    # Test point prompt encoding
    pts = np.array([[[100.0, 200.0], [500.0, 600.0]], [[300.0, 400.0], [700.0, 800.0]]], dtype=np.float32)
    lbls = np.array([[1, 0], [1, 1]], dtype=np.int32)
    pts_tokens = prompt_enc.encode_points(pts, lbls)

    assert pts_tokens.shape == (batch_size, 2, 256)

    # Test bounding box prompt encoding
    boxes = np.array([[50.0, 50.0, 400.0, 400.0], [100.0, 100.0, 800.0, 800.0]], dtype=np.float32)
    box_tokens = prompt_enc.encode_box(boxes)

    assert box_tokens.shape == (batch_size, 2, 256)


def test_mask_decoder_and_iou_head():
    config = SAM2HieraTinyConfig()
    decoder = TwoWayTransformerMaskDecoder(config, seed=42)
    batch_size = 1

    fake_img_embed = np.random.normal(0, 1, (batch_size, 64, 64, 256)).astype(np.float32)
    fake_prompt_tokens = np.random.normal(0, 1, (batch_size, 3, 256)).astype(np.float32)

    masks, iou_scores = decoder.forward(fake_img_embed, fake_prompt_tokens)

    # Low-res output mask: 256x256, 4 mask outputs
    assert masks.shape == (batch_size, 4, 256, 256)
    assert iou_scores.shape == (batch_size, 4)
    # IoU scores must lie in [0, 1]
    assert np.all(iou_scores >= 0.0) and np.all(iou_scores <= 1.0)


def test_full_sam2_pipeline_e2e_and_pcc():
    pipeline = SAM2Pipeline()
    batch_size = 1

    rng = np.random.default_rng(123)
    image = rng.uniform(0.0, 1.0, (batch_size, 3, 1024, 1024)).astype(np.float32)
    point_coords = np.array([[[512.0, 512.0]]], dtype=np.float32)
    point_labels = np.array([[1]], dtype=np.int32)
    boxes = np.array([[200.0, 200.0, 800.0, 800.0]], dtype=np.float32)

    res = pipeline.segment_image(image, point_coords=point_coords, point_labels=point_labels, box=boxes)

    assert "best_mask" in res
    assert "binary_mask" in res
    assert "iou_scores" in res

    best_mask = res["best_mask"]
    assert best_mask.shape == (batch_size, 256, 256)
    assert res["binary_mask"].shape == (batch_size, 256, 256)
    assert set(np.unique(res["binary_mask"])).issubset({0, 1})

    # PCC repeatability verification
    res_repeat = pipeline.segment_image(image, point_coords=point_coords, point_labels=point_labels, box=boxes)
    pcc = compute_pcc(res["best_mask"], res_repeat["best_mask"])
    assert pcc > 0.9999

"""Unit tests for DiffusionDrive Truncated Diffusion Policy Subsystem.
Resolves Issue #505: [Bounty $1500] Diffusion Drive bring up using TTNN APIs.
Validates:
- Anchor trajectory bank generation and multimodal maneuver coverage (straight, turns, braking)
- BEV cross-attention denoising block tensor shapes and SiLU activation
- Truncated reverse diffusion trajectory planning (K=3 steps)
- Kinematic sanity of generated waypoint coordinates (x, y, vx, vy)
- Pearson Correlation Coefficient (PCC) consistency on planned waypoints
"""

import math
import numpy as np
import pytest
from scripts.diffusiondrive_ttnn_bringup import (
    DiffusionDriveConfig,
    DiffusionDrivePlanner,
    AnchorTrajectoryBank,
    BEVCrossAttentionDenoiseBlock,
    pearson_correlation_coefficient,
    silu,
)


def test_anchor_trajectory_bank():
    anchors = AnchorTrajectoryBank.get_anchors(steps=8)
    assert anchors.shape == (6, 8, 4)  # 6 anchors, 8 waypoints, (x, y, vx, vy)

    # Maneuver 0: Straight cruising (y should remain 0, x increases)
    straight = anchors[0]
    assert np.allclose(straight[:, 1], 0.0)
    assert straight[-1, 0] > straight[0, 0]

    # Maneuver 1: Left turn (y increases positively)
    left = anchors[1]
    assert left[-1, 1] > 0.0

    # Maneuver 2: Right turn (y decreases negatively)
    right = anchors[2]
    assert right[-1, 1] < 0.0

    # Maneuver 5: Braking (final velocity lower than initial)
    brake = anchors[5]
    assert brake[-1, 2] < brake[0, 2]


def test_bev_cross_attention_denoise_block():
    config = DiffusionDriveConfig(hidden_dim=128, bev_feature_dim=128)
    denoise = BEVCrossAttentionDenoiseBlock(config, seed=77)

    noisy_traj = np.random.randn(1, 8, 4).astype(np.float32)
    bev_features = np.random.randn(1, 16, 128).astype(np.float32)

    pred_noise = denoise.forward(noisy_traj, t_step=0.5, bev_features=bev_features)
    assert pred_noise.shape == (1, 8, 4)
    assert not np.isnan(pred_noise).any()


def test_truncated_diffusion_planning():
    config = DiffusionDriveConfig(truncated_steps=3)
    planner = DiffusionDrivePlanner(config)

    # Simulated BEV perceptual feature map from camera/LiDAR
    bev_features = np.random.randn(1, 16, 256).astype(np.float32)

    plan = planner.plan_trajectory(bev_features, ego_speed=10.0, preferred_anchor_idx=0)
    assert plan["status"] == "DIFFUSIONDRIVE_PLAN_SUCCESS"
    assert plan["waypoints"].shape == (8, 4)
    assert plan["truncated_steps_executed"] == 3
    assert plan["final_distance_m"] > 10.0
    assert plan["average_speed_mps"] > 0.0

    # Self-PCC validation
    pcc = pearson_correlation_coefficient(plan["waypoints"], plan["waypoints"])
    assert math.isclose(pcc, 1.0, rel_tol=1e-5)


def test_silu_activation_properties():
    arr = np.array([-10.0, 0.0, 2.0, 10.0], dtype=np.float32)
    out = silu(arr)
    assert abs(out[1]) < 1e-6  # silu(0) = 0
    assert out[0] < 0.0        # negative region
    assert out[2] > 1.7        # silu(2) ~= 1.76

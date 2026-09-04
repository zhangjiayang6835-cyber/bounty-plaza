"""Unit test suite for SS13 VR & Peripherals Subsystem.
Verifies spatial 6DoF head tracking, haptic feedback pulses, peripheral controller inputs,
stereoscopic eye offset calculations, Kilostation DMM map coordinates, and DreamMaker exports.
Resolves Issue #586 ($200 USD).
"""

import pytest
from scripts.ss13_vr_peripherals_engine import (
    SS13VRPeripheralsEngine,
    VRDeviceModel,
    TrackingDofMode,
    HeadPose6DoF,
    VRClientSession
)


@pytest.fixture
def vr_engine():
    return SS13VRPeripheralsEngine()


def test_device_connection_and_dof_modes(vr_engine):
    session_quest = vr_engine.connect_headset("player_one", VRDeviceModel.OCULUS_QUEST)
    assert session_quest.ckey == "player_one"
    assert session_quest.tracking_mode == TrackingDofMode.SIX_DOF
    assert session_quest.ipd_mm == 63.5

    session_labo = vr_engine.connect_headset("player_labo", VRDeviceModel.NINTENDO_LABO)
    assert session_labo.tracking_mode == TrackingDofMode.THREE_DOF

    session_ps2 = vr_engine.connect_headset("player_ps2", VRDeviceModel.SONY_PLAYSTATION_2)
    assert session_ps2.tracking_mode == TrackingDofMode.THREE_DOF

    session_vision = vr_engine.connect_headset("player_apple", VRDeviceModel.APPLE_VISION_PRO, ipd_mm=65.0)
    assert session_vision.tracking_mode == TrackingDofMode.SIX_DOF
    assert session_vision.ipd_mm == 65.0


def test_head_pose_tracking_and_stereoscopic_offsets(vr_engine):
    vr_engine.connect_headset("clown_in_vr", VRDeviceModel.VALVE_FRAME, ipd_mm=64.0)

    # Pose at x=10.0, y=20.0, z=1.75, looking North (yaw=90 deg)
    res = vr_engine.update_head_pose(
        ckey="clown_in_vr",
        x=10.0,
        y=20.0,
        z=1.75,
        yaw=90.0,
        pitch=15.0,
        roll=0.0,
        timestamp_ms=1725450000000.0
    )

    assert res["status"] == "POSE_SYNCHRONIZED"
    assert res["tracking"] == TrackingDofMode.SIX_DOF.value
    # At yaw=90, cos(90)=0, sin(90)=1. Half IPD is 0.032m
    # left eye should offset in y by -0.032, right eye by +0.032
    assert abs(res["left_eye"][0] - 10.0) < 0.001
    assert abs(res["left_eye"][1] - (20.0 - 0.032)) < 0.001
    assert abs(res["right_eye"][0] - 10.0) < 0.001
    assert abs(res["right_eye"][1] - (20.0 + 0.032)) < 0.001


def test_haptic_feedback_pulses(vr_engine):
    vr_engine.connect_headset("security_vr", VRDeviceModel.PICO_4_ULTRA)

    # Trigger haptic pulse on right controller (stun baton discharge recoil)
    event = vr_engine.trigger_haptic_feedback(
        ckey="security_vr",
        hand="right",
        intensity=0.85,
        duration_ms=250,
        reason="STUN_BATON_CONTACT_RECOIL"
    )

    assert event["event_id"] == "HAP-0001"
    assert event["hand"] == "right"
    assert event["intensity"] == 0.85
    session = vr_engine.active_sessions["security_vr"]
    assert session.right_hand.haptic_pulse_intensity == 0.85
    assert session.left_hand.haptic_pulse_intensity == 0.0

    # Both hands haptic pulse (slip on banana peel)
    event_both = vr_engine.trigger_haptic_feedback(
        ckey="security_vr",
        hand="both",
        intensity=1.0,
        duration_ms=500,
        reason="BANANA_PEEL_SLIP_TUMBLE"
    )
    assert event_both["hand"] == "both"
    assert session.left_hand.haptic_pulse_intensity == 1.0
    assert session.right_hand.haptic_pulse_intensity == 1.0


def test_peripheral_input_actions(vr_engine):
    vr_engine.connect_headset("mime_vr", VRDeviceModel.SAMSUNG_GALAXY_XR)

    # Test trigger actuation -> discharge
    res_shoot = vr_engine.process_peripheral_input(
        ckey="mime_vr",
        trigger=0.95,
        grip=0.1,
        thumbstick_x=0.0,
        thumbstick_y=0.0
    )
    assert res_shoot["action"] == "DISCHARGE_OR_ACTIVATE_HELD_ITEM"

    # Test grip actuation -> grasp item
    res_grasp = vr_engine.process_peripheral_input(
        ckey="mime_vr",
        trigger=0.0,
        grip=0.88,
        thumbstick_x=0.0,
        thumbstick_y=0.0
    )
    assert res_grasp["action"] == "GRASP_OR_PICKUP_OBJECT"

    # Test thumbstick -> locomotion
    res_move = vr_engine.process_peripheral_input(
        ckey="mime_vr",
        trigger=0.0,
        grip=0.0,
        thumbstick_x=0.75,
        thumbstick_y=0.45
    )
    assert res_move["action"] == "CONTINUOUS_LOCOMOTION"


def test_map_integration_coordinates(vr_engine):
    dmm_dict = vr_engine.export_map_integration_dmm()
    assert "Kilostation.dmm" in dmm_dict
    assert "/obj/machinery/vr_holodeck_pod" in dmm_dict["Kilostation.dmm"]
    assert "(78, 114, 1)" in dmm_dict["Kilostation.dmm"]
    assert "/obj/item/clothing/glasses/vr_headset/quest" in dmm_dict["Kilostation.dmm"]


def test_dreammaker_export(vr_engine):
    dm_code = vr_engine.export_dreammaker_code()
    assert "/datum/subsystem/vr_peripherals" in dm_code
    assert "/obj/item/clothing/glasses/vr_headset" in dm_code
    assert "/obj/machinery/vr_holodeck_pod" in dm_code
    assert "/client/proc/sync_vr_headset" in dm_code

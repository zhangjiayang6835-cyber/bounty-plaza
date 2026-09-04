"""Unit and integration tests for Desynchronized Client Prediction and Rubberbanding Movement.
Resolves Issue #689: [BOUNTY] [$670 USD] [HARD] Replace Action delays from high ping with rubberbanding.
"""

import pytest
from scripts.rubberband_movement import (
    ClientPredictiveMovement,
    ServerMovementAuthority,
    Direction,
    MovePacket,
    ServerAckPacket,
    DM_RUBBERBAND_MOVEMENT_SPEC,
)


@pytest.fixture
def sync_env():
    server = ServerMovementAuthority(initial_x=10, initial_y=10)
    client = ClientPredictiveMovement(initial_x=10, initial_y=10, simulated_ping_ms=250.0)
    return server, client


def test_zero_latency_immediate_client_movement(sync_env):
    """Verifies that client movement occurs immediately without action delay waiting for network round-trips."""
    server, client = sync_env

    # Client initiates 3 quick steps North
    packet1, immediate1 = client.input_move(Direction.NORTH, timestamp_ms=100.0)
    assert immediate1 is True
    assert client.client_x == 10 and client.client_y == 11
    assert len(client.unacked_packets) == 1

    packet2, immediate2 = client.input_move(Direction.NORTH, timestamp_ms=150.0)
    assert immediate2 is True
    assert client.client_x == 10 and client.client_y == 12
    assert len(client.unacked_packets) == 2


def test_server_validation_and_clean_ack(sync_env):
    """Verifies that when client and server agree on path with no obstacles, packets are cleanly acknowledged."""
    server, client = sync_env

    # Step East
    packet, _ = client.input_move(Direction.EAST, timestamp_ms=200.0)
    assert client.client_x == 11 and client.client_y == 10

    # Server receives and processes packet
    ack = server.process_client_packet(packet)
    assert ack.accepted is True
    assert ack.rubberband_required is False
    assert server.server_x == 11 and server.server_y == 10

    # Client receives ack
    client.receive_server_ack(ack)
    assert len(client.unacked_packets) == 0
    assert client.rubberband_snap_count == 0


def test_obstacle_collision_triggers_rubberband_snapback(sync_env):
    """Verifies that hitting a solid wall causes the server to reject the move and snap the client back."""
    server, client = sync_env

    # Place wall at (10, 11)
    server.add_obstacle(10, 11)

    # Client optimistically walks North into the wall (unaware of obstacle yet due to high ping)
    packet1, _ = client.input_move(Direction.NORTH, timestamp_ms=300.0)
    assert client.client_y == 11  # Client optimistically at 11

    # Server evaluates packet
    ack = server.process_client_packet(packet1)
    assert ack.accepted is False
    assert ack.rubberband_required is True
    assert ack.reason == "solid_obstacle_collision"
    assert server.server_y == 10  # Server holds firm at 10

    # Client processes rubberband snapback
    client.receive_server_ack(ack)
    assert client.rubberband_snap_count == 1
    assert client.client_y == 10  # Client snapped back to 10!
    assert len(client.unacked_packets) == 0


def test_rubberband_replays_pending_future_inputs(sync_env):
    """Verifies that when a rubberband occurs, valid subsequent inputs in the pipeline are re-evaluated."""
    server, client = sync_env

    # Obstacle at (10, 11)
    server.add_obstacle(10, 11)

    # Client enters move North (seq 1), followed immediately by move East (seq 2)
    packet1, _ = client.input_move(Direction.NORTH, timestamp_ms=400.0)  # tries (10, 11)
    packet2, _ = client.input_move(Direction.EAST, timestamp_ms=450.0)   # tries (11, 11)

    assert client.client_x == 11 and client.client_y == 11
    assert len(client.unacked_packets) == 2

    # Server receives seq 1 and rejects it
    ack1 = server.process_client_packet(packet1)
    assert ack1.rubberband_required is True

    # Client receives rubberband for seq 1: snaps back to (10, 10) and replays seq 2 (East) -> lands on (11, 10)
    client.receive_server_ack(ack1)
    assert client.client_x == 11 and client.client_y == 10
    assert len(client.unacked_packets) == 1
    assert client.unacked_packets[0].seq == 2


def test_byond_dm_specification_export():
    """Verifies that BYOND / DM source specification includes component hooks and rubberband dispatch."""
    assert "/datum/component/client_prediction" in DM_RUBBERBAND_MOVEMENT_SPEC
    assert "send_rubberband_snap" in DM_RUBBERBAND_MOVEMENT_SPEC
    assert "glide_size" in DM_RUBBERBAND_MOVEMENT_SPEC
    assert "COMSIG_MOB_PREDICTED_STEP" in DM_RUBBERBAND_MOVEMENT_SPEC

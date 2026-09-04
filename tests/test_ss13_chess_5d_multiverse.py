"""Unit tests for SS13 5D Chess With Multiverse Time Travel Arcade Mini-Game (Issue #599)."""

import pytest
from scripts.ss13_chess_5d_multiverse import (
    ArcadeGameMode,
    Chess5DArcadeMachine,
    ChessColor,
    Coord5D,
    PieceType,
    QueenFollowerMob,
)


def test_arcade_game_initialization():
    arcade = Chess5DArcadeMachine()
    res = arcade.start_game(ArcadeGameMode.SOLO_VS_BOT, "ckey_grandmaster")
    assert res["status"] == "GAME_INITIALIZED"
    assert res["mode"] == "solo_vs_bot"
    assert res["white"] == "ckey_grandmaster"
    assert res["black"] == "STATION_CHESS_BOT_AI"
    assert arcade.is_active is True
    assert len(arcade.timelines) == 1
    assert 1 in arcade.timelines[0]
    # Check 32 initial pieces (16 white, 16 black)
    assert len(arcade.timelines[0][1]) == 32


def test_standard_spatial_move_advances_time():
    arcade = Chess5DArcadeMachine()
    arcade.start_game(ArcadeGameMode.SOLO_VS_BOT, "ckey_grandmaster")

    # Move white pawn from E2 (4, 1, 1, 0, 0) to E4 (4, 3, 2, 0, 0)
    from_c = Coord5D(4, 1, 1, 0, 0)
    to_c = Coord5D(4, 3, 2, 0, 0)

    move_res = arcade.make_move(from_c, to_c, "ckey_grandmaster")
    assert move_res["status"] == "MOVE_EXECUTED"
    assert move_res["piece"] == "pawn"
    assert move_res["is_time_travel"] is False
    assert 2 in arcade.timelines[0]
    assert (4, 3) in arcade.timelines[0][2]
    assert (4, 1) not in arcade.timelines[0][2]
    assert arcade.current_turn_color == ChessColor.BLACK


def test_multiverse_branching_time_travel_move():
    arcade = Chess5DArcadeMachine()
    arcade.start_game(ArcadeGameMode.SOLO_VS_BOT, "ckey_player1")

    # White moves pawn
    arcade.make_move(Coord5D(4, 1, 1, 0, 0), Coord5D(4, 3, 2, 0, 0), "ckey_player1")
    # Black bot responds
    arcade.bot_play_turn()

    # White makes time-travel knight leap into the past (t=1, l=0)
    # Moving back from t=3 to t=1 creates a new branched timeline
    from_knight = Coord5D(1, 0, 3, 0, 0)
    to_past = Coord5D(2, 2, 1, 0, 0)  # Target past board state at t=1

    tt_res = arcade.make_move(from_knight, to_past, "ckey_player1")
    assert tt_res["is_time_travel"] is True
    assert tt_res["new_timeline_branched"] is not None
    assert len(arcade.timelines) == 2


def test_turn_validation_and_unauthorized_player_rejection():
    arcade = Chess5DArcadeMachine()
    arcade.start_game(ArcadeGameMode.MULTIPLAYER_PVP, "ckey_alice", "ckey_bob")

    # Bob cannot move on Alice's turn
    with pytest.raises(PermissionError):
        arcade.make_move(Coord5D(4, 1, 1, 0, 0), Coord5D(4, 3, 2, 0, 0), "ckey_bob")


def test_bot_ai_play_turn():
    arcade = Chess5DArcadeMachine()
    arcade.start_game(ArcadeGameMode.SOLO_VS_BOT, "ckey_human")
    # White moves
    arcade.make_move(Coord5D(4, 1, 1, 0, 0), Coord5D(4, 3, 2, 0, 0), "ckey_human")
    assert arcade.current_turn_color == ChessColor.BLACK

    # Bot plays
    bot_res = arcade.bot_play_turn()
    assert bot_res["status"] == "MOVE_EXECUTED"
    assert arcade.current_turn_color == ChessColor.WHITE


def test_queen_follower_mob_5d_movement():
    queen = QueenFollowerMob(owner_ckey="ckey_winner", current_coord_5d=Coord5D(3, 0, 0, 0, 0))

    # Valid orthogonal move along X (3,0,0,0,0) -> (7,0,0,0,0)
    assert queen.can_move_to_5d(Coord5D(7, 0, 0, 0, 0)) is True

    # Valid diagonal move along X and Y (3,0,0,0,0) -> (5,2,0,0,0)
    assert queen.can_move_to_5d(Coord5D(5, 2, 0, 0, 0)) is True

    # Valid 5D hyper-diagonal move across all 5 dimensions equally (+2 on all dims)
    assert queen.can_move_to_5d(Coord5D(5, 2, 2, 2, 2)) is True

    # Invalid unequal knight-like jump
    assert queen.can_move_to_5d(Coord5D(4, 2, 0, 0, 0)) is False

    # Perform valid 5D transit
    res = queen.travel_across_5d(Coord5D(5, 2, 2, 2, 2), station_coord=(102, 110, 1))
    assert res["status"] == "QUEEN_5D_TRANSIT_COMPLETE"
    assert queen.spatial_coord == (102, 110, 1)


def test_dispense_prizes_for_winning_player():
    arcade = Chess5DArcadeMachine()
    arcade.start_game(ArcadeGameMode.SOLO_VS_BOT, "ckey_champion")
    arcade.is_active = False
    arcade.game_winner = "ckey_champion"

    prizes = arcade.dispense_prizes("ckey_champion")
    assert prizes["winner"] == "ckey_champion"
    assert prizes["king_plushie"]["name"] == "King Chess Piece Plushie"
    assert isinstance(prizes["queen_mob"], QueenFollowerMob)

    # Non-winner cannot claim
    with pytest.raises(PermissionError):
        arcade.dispense_prizes("ckey_impostor")


def test_map_and_dreammaker_exports():
    arcade = Chess5DArcadeMachine()
    maps = arcade.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "/obj/machinery/computer/arcade/battle/chess5d" in maps["IceBoxStation.dmm"]

    dm = arcade.export_dreammaker_code()
    assert "/obj/machinery/computer/arcade/battle/chess5d" in dm
    assert "/obj/item/toy/plush/king_chess" in dm
    assert "/mob/living/simple_animal/pet/chess_queen" in dm

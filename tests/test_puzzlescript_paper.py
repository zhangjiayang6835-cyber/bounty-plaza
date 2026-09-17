"""Unit and integration tests for PuzzleScript Sokoban Paper Game Engine.
Resolves Issue #695: [BOUNTY] [$25] [Priority] [Easy] [Agentic] Puzzlescript implementation.
"""

import pytest
from scripts.puzzlescript_paper import (
    PuzzleScriptSokobanGame,
    DM_PUZZLESCRIPT_PAPER_SPEC,
)


@pytest.fixture
def default_game():
    # Simple 1-step win level:
    # #####
    # #@$.#
    # #####
    return PuzzleScriptSokobanGame([
        "#####",
        "#@$.#",
        "#####",
    ])


def test_level_initialization_and_entities(default_game):
    """Verifies that wall, player, box, and target coordinates are correctly mapped."""
    assert default_game.player_pos == (1, 1)
    assert (1, 2) in default_game.boxes
    assert (1, 3) in default_game.targets
    assert (0, 0) in default_game.walls
    assert default_game.is_won is False


def test_player_wall_collision(default_game):
    """Verifies player cannot walk into walls."""
    # Move up into wall at (0, 1)
    moved = default_game.move(-1, 0)
    assert moved is False
    assert default_game.player_pos == (1, 1)


def test_box_push_and_victory_condition(default_game):
    """Verifies pushing a box onto target activates victory."""
    # Push box right from (1, 2) to (1, 3)
    moved = default_game.move(0, 1)
    assert moved is True
    assert default_game.player_pos == (1, 2)
    assert (1, 3) in default_game.boxes
    assert default_game.is_won is True


def test_box_blocked_by_wall(default_game):
    """Verifies box cannot be pushed into a wall."""
    # Push box onto target at (1, 3)
    default_game.move(0, 1)
    assert default_game.player_pos == (1, 2)
    # Attempt pushing box right into wall at (1, 4)
    blocked_push = default_game.move(0, 1)
    assert blocked_push is False
    assert default_game.player_pos == (1, 2)
    assert (1, 3) in default_game.boxes


def test_move_undo_restores_box_and_player(default_game):
    """Verifies that undo accurately rolls back box and player coordinates."""
    initial_player = default_game.player_pos
    initial_boxes = set(default_game.boxes)

    default_game.move(0, 1)
    assert default_game.is_won is True

    # Undo move
    undone = default_game.undo()
    assert undone is True
    assert default_game.player_pos == initial_player
    assert default_game.boxes == initial_boxes
    assert default_game.is_won is False


def test_html5_game_runtime_generation(default_game):
    """Verifies HTML5 bundle generation contains required canvas and script tags."""
    html = default_game.generate_html5_game()
    assert "<!DOCTYPE html>" in html
    assert "PuzzleScript Paper: Sokoban" in html
    assert "function move(dr, dc)" in html
    assert "function undo()" in html
    assert "INITIAL_WALLS" in html
    assert "INITIAL_TARGETS" in html


def test_byond_dm_paper_specification_export():
    """Verifies that DM code contains /obj/item/paper/puzzlescript definition."""
    assert "/obj/item/paper/puzzlescript" in DM_PUZZLESCRIPT_PAPER_SPEC
    assert "open_game_webview" in DM_PUZZLESCRIPT_PAPER_SPEC
    assert "datum/browser/popup" in DM_PUZZLESCRIPT_PAPER_SPEC

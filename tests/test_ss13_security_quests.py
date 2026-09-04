"""Unit tests for SS13 Security Daily Quests & Player Engagement Engine.
Resolves Issue #594: [BOUNTY] [READY FOR AGENT] [$950 USD] ADD DAILY QUESTS FOR SECURITY TO BOOST PLAYER ENGAGEMENT.
"""

import pytest
from scripts.ss13_security_quests import (
    DailySecurityQuest,
    QuestDifficulty,
    MASTER_SECURITY_QUEST_POOL,
    OfficerDailyQuestTracker,
    SecurityEngagementEngine,
)


def test_quest_pool_depth_and_variety():
    # Verify variety is high enough across all four difficulty categories
    assert len(MASTER_SECURITY_QUEST_POOL) >= 15
    difficulties = {q.difficulty for q in MASTER_SECURITY_QUEST_POOL}
    assert QuestDifficulty.EASY in difficulties
    assert QuestDifficulty.MODERATE in difficulties
    assert QuestDifficulty.HARD in difficulties
    assert QuestDifficulty.MYTHICAL in difficulties

    # Check canonical requested examples from Issue #594
    titles = [q.title for q in MASTER_SECURITY_QUEST_POOL]
    assert "Ensure the armory guns are clean" in titles
    assert "Harmbaton the mime" in titles
    assert "Talk to the prisoners in brig" in titles
    assert "Stop the Research Director building ten ais and shoving them in combat mechs" in titles


def test_daily_quest_board_generation():
    engine = SecurityEngagementEngine(epoch_day_override=100)
    board_day_100 = engine.generate_daily_quest_board()
    assert len(board_day_100) == 4

    # Different day must rotate quests
    board_day_101 = engine.generate_daily_quest_board(epoch_day=101)
    assert len(board_day_101) == 4
    # Check that at least some quest rotated
    assert [q.quest_id for q in board_day_100] != [q.quest_id for q in board_day_101]


def test_officer_quest_completion_and_rewards():
    engine = SecurityEngagementEngine(epoch_day_override=50)
    officer = engine.register_officer_roundstart("ckey_cop", "Officer Jenny")
    assert len(officer.assigned_quests) == 4
    assert officer.credits_balance == 0

    first_quest_id = list(officer.assigned_quests.keys())[0]
    first_quest = officer.assigned_quests[first_quest_id]

    res = officer.complete_quest(first_quest_id)
    assert res["status"] == "QUEST_COMPLETED"
    assert res["credits_awarded"] == first_quest.credit_reward
    assert officer.credits_balance == first_quest.credit_reward

    # Completing already completed quest returns idempotent status without extra credits
    res_repeat = officer.complete_quest(first_quest_id)
    assert res_repeat["status"] == "ALREADY_COMPLETED"
    assert officer.credits_balance == first_quest.credit_reward


def test_officer_unassigned_quest_error():
    officer = OfficerDailyQuestTracker(officer_ckey="ckey_officer", officer_name="Deputy Dave")
    with pytest.raises(KeyError, match="not assigned to officer"):
        officer.complete_quest("NONEXISTENT_QUEST_ID")


def test_spending_credits_at_vendor_or_cargo():
    officer = OfficerDailyQuestTracker(
        officer_ckey="ckey_officer",
        officer_name="Sergeant John",
        credits_balance=600
    )

    # Buy energy gun charge pack
    purchase = officer.spend_credits_at_vendor_or_cargo(250, "Energy Charge Pack")
    assert purchase["status"] == "PURCHASE_SUCCESSFUL"
    assert purchase["item"] == "Energy Charge Pack"
    assert officer.credits_balance == 350

    # Overspending throws RuntimeError
    with pytest.raises(RuntimeError, match="Insufficient credits"):
        officer.spend_credits_at_vendor_or_cargo(500, "High-End Donut Box")

    # Non-positive amount throws ValueError
    with pytest.raises(ValueError, match="Purchase amount must be positive"):
        officer.spend_credits_at_vendor_or_cargo(0, "Air")


def test_dreammaker_export():
    engine = SecurityEngagementEngine()
    dm_code = engine.export_dreammaker_definitions()
    assert "/datum/security_daily_quest" in dm_code
    assert "award_credits" in dm_code
    assert "playsound" in dm_code

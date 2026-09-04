"""Unit tests for SS13 Gachafication (Total Gachafication) Engine.
Resolves Issue #642: [BOUNTY][$7,500][AGENTIC] SS13 Gachafication.
Upstream Reference: Iamgoofball/-tg-station#155.
"""

import pytest
from scripts.ss13_gachafication_engine import (
    SS13GachaficationEngine,
    GachaItem,
    Rarity,
    BannerType,
    PullResult,
    GACHA_CATALOG,
)


@pytest.fixture
def gacha():
    return SS13GachaficationEngine(executive_name="Executive John Nanotrasen")


def test_daily_login_rewards(gacha):
    initial_credits = gacha.credits
    initial_tokens = gacha.antag_tokens

    claim = gacha.claim_daily_rewards()
    assert claim["claimed"] is True
    assert gacha.credits == initial_credits + 500
    assert gacha.antag_tokens == initial_tokens + 20


def test_standard_pull_deducts_currency(gacha):
    initial_credits = gacha.credits
    res = gacha.pull_banner(banner=BannerType.STANDARD, use_antag_tokens=False)

    assert gacha.credits == initial_credits - 100
    assert gacha.pity_counter == 1
    assert len(gacha.roster) == 1
    assert isinstance(res, PullResult)


def test_token_pull_deducts_antag_tokens(gacha):
    initial_tokens = gacha.antag_tokens
    res = gacha.pull_banner(banner=BannerType.EMERGENCY, use_antag_tokens=True)

    assert gacha.antag_tokens == initial_tokens - 10
    assert len(gacha.roster) == 1


def test_insufficient_funds_error(gacha):
    gacha.credits = 50
    with pytest.raises(ValueError) as exc:
        gacha.pull_banner(use_antag_tokens=False)
    assert "Insufficient Credits" in str(exc.value)

    gacha.antag_tokens = 5
    with pytest.raises(ValueError) as exc:
        gacha.pull_banner(use_antag_tokens=True)
    assert "Insufficient Antag Tokens" in str(exc.value)


def test_hard_pity_trigger(gacha):
    gacha.credits = 100000  # Plenty of credits
    gacha.pity_counter = 89  # One pull away from hard pity

    res = gacha.pull_banner(banner=BannerType.STANDARD, fixed_roll=0.99)
    assert res.is_pity_trigger is True
    assert res.item.rarity == Rarity.FIVE_STAR
    assert gacha.pity_counter == 0


def test_department_deployment_and_clown_disaster(gacha):
    clown1 = GachaItem("cln_01", "Banana Slip Clown", Rarity.THREE_STAR, "Service", False)
    clown2 = GachaItem("cln_02", "Honking Clown", Rarity.THREE_STAR, "Service", False)

    dep1 = gacha.deploy_character("Security", clown1)
    assert dep1["department"] == "Security"
    assert dep1["team_size"] == 1
    assert dep1["synergy_warning"] is None

    dep2 = gacha.deploy_character("Security", clown2)
    assert dep2["team_size"] == 2
    assert "Slip-N-Slide Police State" in dep2["synergy_warning"]


def test_shift_simulation_and_robust_pity(gacha):
    # Deploy 3 very fragile assistants
    for _ in range(3):
        fragile = GachaItem("ast_01", "Disposable Assistant", Rarity.ONE_STAR, "Assistant", False, base_survival_skill=0.0)
        gacha.deploy_character("Medical", fragile)

    res = gacha.simulate_shift_cycle()
    assert res["shift_status"] == "SHIFT_COMPLETED"
    assert res["total_deployed"] == 3
    assert res["casualties"] == 3
    assert res["mortality_rate"] == 100.0
    assert res["robust_pity_triggered"] is True
    assert gacha.robust_pity_active is True

    # Next pull should trigger robust pity guaranteeing 5-star
    pull = gacha.pull_banner(banner=BannerType.STANDARD, fixed_roll=0.99)
    assert pull.is_robust_pity is True
    assert pull.item.rarity == Rarity.FIVE_STAR
    assert gacha.robust_pity_active is False


def test_dreammaker_export_syntax(gacha):
    dm = gacha.export_dreammaker_code()
    assert "/datum/gacha_controller" in dm
    assert "pity_count >= 90" in dm
    assert "robust_pity" in dm

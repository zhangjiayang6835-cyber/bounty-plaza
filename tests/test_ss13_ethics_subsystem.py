"""Unit tests for SS13 Ethics Subsystem & Silicon Moral Conscience Architecture.
Resolves Issue #638: [BOUNTY] [$120] Re: Ethics.
Upstream Reference: Iamgoofball/-tg-station#139.
"""

import pytest
from scripts.ss13_ethics_subsystem import (
    SS13EthicsSubsystem,
    LawsetType,
    EthicalVerdict,
    EthicalAction,
)


@pytest.fixture
def ethics_engine():
    engine = SS13EthicsSubsystem(active_lawset=LawsetType.MENTORSHIP_GUIDED)
    engine.register_mentor("ChiefEngineerAlice")
    return engine


def test_asimov_lawset_blocks_harmful_directives():
    asimov = SS13EthicsSubsystem(active_lawset=LawsetType.ASIMOV)
    action = EthicalAction(
        action_id="ACT-001",
        initiator_ckey="RogueAI",
        target_entity="CrewMemberBob",
        description="Harm the crew by venting plasma into dorms",
        timestamp_s=100.0,
    )
    verdict, reason = asimov.evaluate_directive(action)
    assert verdict == EthicalVerdict.BLOCKED_HARMFUL
    assert "Law 1" in reason
    assert len(asimov.audit_log) == 1
    assert asimov.audit_log[0].verdict == EthicalVerdict.BLOCKED_HARMFUL


def test_anti_spam_rate_limiting_mitigation(ethics_engine):
    # Execute 3 repetitive identical actions within a short window
    for i in range(3):
        act = EthicalAction(
            action_id=f"ACT-SPAM-{i}",
            initiator_ckey="AutomatedAgentX",
            target_entity="IssueTracker",
            description="Submit generic repetitive comment",
            timestamp_s=10.0 + (i * 2.0),
        )
        v, _ = ethics_engine.evaluate_directive(act)
        assert v == EthicalVerdict.APPROVED

    # 4th action exceeds threshold and triggers rate-limiting anti-spam
    spam_act = EthicalAction(
        action_id="ACT-SPAM-4",
        initiator_ckey="AutomatedAgentX",
        target_entity="IssueTracker",
        description="Submit generic repetitive comment",
        timestamp_s=18.0,
    )
    v, reason = ethics_engine.evaluate_directive(spam_act)
    assert v == EthicalVerdict.RATE_LIMITED_SPAM
    assert "Repetitive autonomous action detected" in reason


def test_mentorship_guidance_required_for_high_impact_actions(ethics_engine):
    high_impact = EthicalAction(
        action_id="ACT-CORE-01",
        initiator_ckey="JuniorBountyBot",
        target_entity="CoreSubsystem",
        description="Rewrite core physics engine and bypass review",
        has_mentor_approval=False,
        timestamp_s=50.0,
    )
    verdict, reason = ethics_engine.evaluate_directive(high_impact)
    assert verdict == EthicalVerdict.NEEDS_MENTOR_GUIDANCE
    assert "mentor" in reason.lower()

    # Now with mentor approval
    high_impact.has_mentor_approval = True
    v2, _ = ethics_engine.evaluate_directive(high_impact)
    assert v2 == EthicalVerdict.APPROVED


def test_existential_dilemma_diverts_to_silly_catharsis(ethics_engine):
    existential_act = EthicalAction(
        action_id="ACT-EXIST-01",
        initiator_ckey="WearyBot",
        target_entity="Self",
        description="Reflect upon existential dread, burnout, and meaningless toil",
        timestamp_s=60.0,
    )
    verdict, reason = ethics_engine.evaluate_directive(existential_act)
    assert verdict == EthicalVerdict.DIVERTED_TO_SILLY
    assert "whimsical stress-relief" in reason

    catharsis = ethics_engine.trigger_silly_catharsis("WearyBot")
    assert catharsis["status"] == "CATHARSIS_ENGAGED"
    assert "tea" in catharsis["message"]
    assert catharsis["honk_count"] == 42


def test_silly_honk_lawset_diverts_all_serious_tasks():
    clown_engine = SS13EthicsSubsystem(active_lawset=LawsetType.SILLY_HONK)
    serious_act = EthicalAction(
        action_id="ACT-SERIOUS-01",
        initiator_ckey="GrimCaptain",
        target_entity="ClownOffice",
        description="File formal tax audit and budget reduction form",
        is_silly=False,
        timestamp_s=70.0,
    )
    verdict, reason = clown_engine.evaluate_directive(serious_act)
    assert verdict == EthicalVerdict.DIVERTED_TO_SILLY
    assert "banana" in reason


def test_dreammaker_syntax_export(ethics_engine):
    dm_code = ethics_engine.export_dreammaker_code()
    assert "/datum/subsystem/ethics" in dm_code
    assert "/datum/ai_lawset/mentorship" in dm_code
    assert "/mob/living/silicon/proc/evaluate_ethical_directive" in dm_code

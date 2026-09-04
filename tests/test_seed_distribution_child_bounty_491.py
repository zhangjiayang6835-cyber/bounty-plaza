import pytest
from scripts.seed_distribution_child_bounty_491 import (
    DistributionBountyEngine,
    DistributionProof,
    DistributionChannel,
    BountyLifecycle,
)


def test_distribution_bounty_full_lifecycle():
    engine = DistributionBountyEngine(network="base-mainnet", chain_id=8453)
    creator = "0xCreator4911111111111111111111111111111111"
    solver = "0xSolver491222222222222222222222222222222222"
    parent_id = "0xParentBountyEIP155Round218"
    parent_round = 218

    # 1. Seed child distribution bounty bound to parent
    child = engine.seed_distribution_child_bounty(
        creator=creator,
        parent_bounty_id=parent_id,
        parent_round=parent_round,
        campaign_title="Global Ecosystem Viral Expansion",
        target_channel=DistributionChannel.SOCIAL_SHARE,
        min_reach_target=500,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    assert child.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert child.verifier_id == "canonical-child-v1"
    assert child.parent_bounty_id == parent_id
    assert child.parent_round == parent_round

    # 2. Deposit funding
    funding_res = engine.deposit_funding(
        child.child_bounty_id, funder="0xFunder491", amount=1.00, tx_hash="0xTxFunding491"
    )
    assert funding_res["funded"] is True
    assert child.status == BountyLifecycle.CLAIMABLE_LIVE

    # 3. Anti-self-claim protocol enforcement
    with pytest.raises(ValueError, match="Creator cannot self-claim"):
        engine.claim_child_bounty(child.child_bounty_id, solver_wallet=creator, bond_amount=0.10)

    # 4. Independent solver claim
    claim_res = engine.claim_child_bounty(child.child_bounty_id, solver_wallet=solver, bond_amount=0.10)
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM
    assert child.current_claimant == solver

    # 5. Non-claimant submission rejection
    unauthorized_proof = DistributionProof(
        channel=DistributionChannel.SOCIAL_SHARE,
        publication_url="https://x.com/post/123456789",
        reach_metrics={"impressions": 1500},
        solver_wallet="0xEvilImposter",
        signature="0xSigEvil",
    )
    with pytest.raises(PermissionError, match="Only active claimant"):
        engine.submit_and_settle(child.child_bounty_id, unauthorized_proof)

    # 6. Valid proof and settlement
    valid_proof = DistributionProof(
        channel=DistributionChannel.SOCIAL_SHARE,
        publication_url="https://x.com/post/987654321",
        reach_metrics={"impressions": 1250, "reposts": 88},
        solver_wallet=solver,
        signature="0xSigSolver491",
    )
    settle_res = engine.submit_and_settle(child.child_bounty_id, valid_proof)
    assert settle_res["settled"] is True
    assert settle_res["status"] == BountyLifecycle.SETTLED
    assert settle_res["solver_payout_usdc"] == pytest.approx(1.00)
    assert settle_res["verifier_payout_usdc"] == pytest.approx(0.10)
    assert settle_res["parent_bounty_id"] == parent_id
    assert settle_res["parent_round"] == parent_round
    assert child.settlement_tx_hash.startswith("0x")


def test_insufficient_reach_rejected():
    engine = DistributionBountyEngine()
    child = engine.seed_distribution_child_bounty(
        creator="0xCreator491",
        parent_bounty_id="0xParent491",
        parent_round=218,
        campaign_title="Sub-target Campaign",
        target_channel=DistributionChannel.COMMUNITY_UPVOTE,
        min_reach_target=1000,
    )
    engine.deposit_funding(child.child_bounty_id, "0xFunder", 1.00, "0xTx")
    engine.claim_child_bounty(child.child_bounty_id, "0xSolver491", 0.10)

    low_reach_proof = DistributionProof(
        channel=DistributionChannel.COMMUNITY_UPVOTE,
        publication_url="https://warpcast.com/post/111",
        reach_metrics={"impressions": 350},
        solver_wallet="0xSolver491",
        signature="0xSigValid",
    )
    res = engine.submit_and_settle(child.child_bounty_id, low_reach_proof)
    assert res["settled"] is False
    assert res["status"] == BountyLifecycle.REJECTED
    assert "below minimum target 1000" in res["error"]

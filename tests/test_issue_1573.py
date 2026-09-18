"""
Unit and integration test suite for Issue #1573: Boxy PR guard, humor review, and settlement engine.
"""

from decimal import Decimal
import os
import tempfile
import pytest

from packages.omni_boxy_guard import (
    BoxyReviewBot,
    BoxySettlementEngine,
    Contributor,
    HumorAnalysisEngine,
    HumorClassification,
    MembershipStatus,
    PRAction,
    PreemptiveGuard,
    PullRequest,
    WhitelistManager,
)


class TestWhitelistManager:
    """Tests for WhitelistManager state, normalization, and persistence."""

    def test_add_and_check_user(self):
        """Test adding users and case-insensitive check."""
        wm = WhitelistManager()
        assert wm.add_user("alice") is True
        assert wm.add_user("alice") is False
        assert wm.is_whitelisted("alice") is True
        assert wm.is_whitelisted("Alice") is True
        assert wm.is_whitelisted("@ALICE") is True
        assert wm.is_whitelisted("bob") is False

    def test_invalid_username(self):
        """Test handling of invalid or empty usernames."""
        wm = WhitelistManager()
        assert wm.add_user("") is False
        assert wm.add_user("   ") is False
        assert wm.is_whitelisted("") is False

    def test_remove_user(self):
        """Test user removal."""
        wm = WhitelistManager(["alice", "bob"])
        assert wm.is_whitelisted("bob") is True
        assert wm.remove_user("bob") is True
        assert wm.remove_user("bob") is False
        assert wm.is_whitelisted("bob") is False

    def test_clear_and_count(self):
        """Test count and clearing entries."""
        wm = WhitelistManager(["user1", "user2", "user3"])
        assert wm.count() == 3
        assert wm.get_whitelist() == ["user1", "user2", "user3"]
        wm.clear()
        assert wm.count() == 0
        assert not wm.get_whitelist()

    def test_persistence_roundtrip(self):
        """Test disk persistence and retrieval."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "whitelist.json")
            wm1 = WhitelistManager(["carol", "dave"], storage_path=file_path)
            wm1.save_to_file(file_path)

            wm2 = WhitelistManager(storage_path=file_path)
            assert wm2.is_whitelisted("carol") is True
            assert wm2.is_whitelisted("dave") is True
            assert wm2.is_whitelisted("eve") is False


class TestPreemptiveGuard:
    """Tests for PreemptiveGuard organizational authorization and gate checks."""

    @pytest.fixture
    def guard(self):
        """Fixture providing PreemptiveGuard with configured whitelist."""
        wm = WhitelistManager(["trusted_coder"])
        return PreemptiveGuard(whitelist_manager=wm, organization="OmniBlocks", ping_target="@OmniBlocks/coders")

    def test_bot_author_bypasses_close(self, guard):
        """Verify bot authors are not pre-emptively closed."""
        bot = Contributor(username="dependabot[bot]", is_bot=True)
        pr = PullRequest(pr_number=10, title="Bump deps", description="Automated bump", author=bot)
        result = guard.check_pull_request(pr)
        assert result.should_close is False
        assert result.author_status == MembershipStatus.BOT

    def test_org_member_bypasses_close(self, guard):
        """Verify organization members are authorized."""
        member = Contributor(username="alice", organization_member=True)
        pr = PullRequest(pr_number=11, title="Core logic", description="Feature", author=member)
        result = guard.check_pull_request(pr)
        assert result.should_close is False
        assert result.author_status == MembershipStatus.ORGANIZATION_MEMBER

    def test_org_role_bypasses_close(self, guard):
        """Verify maintainer roles bypass pre-emptive closure."""
        collab = Contributor(username="bob", role="COLLABORATOR")
        pr = PullRequest(pr_number=12, title="Collab patch", description="Patch", author=collab)
        result = guard.check_pull_request(pr)
        assert result.should_close is False
        assert result.author_status == MembershipStatus.ORGANIZATION_MEMBER

    def test_whitelisted_contributor_bypasses_close(self, guard):
        """Verify whitelisted external contributors bypass closure."""
        whitelisted = Contributor(username="trusted_coder", organization_member=False)
        pr = PullRequest(pr_number=13, title="Community fix", description="Bugfix", author=whitelisted)
        result = guard.check_pull_request(pr)
        assert result.should_close is False
        assert result.author_status == MembershipStatus.WHITELISTED

    def test_external_contributor_preemptively_closed(self, guard):
        """Verify non-member unlisted contributors have PRs pre-emptively closed."""
        stranger = Contributor(username="unknown_user", organization_member=False, role="NONE")
        pr = PullRequest(pr_number=14, title="External PR", description="Submission", author=stranger)
        result = guard.check_pull_request(pr)
        assert result.should_close is True
        assert result.author_status == MembershipStatus.EXTERNAL_CONTRIBUTOR
        assert result.target_role_ping == "@OmniBlocks/coders"
        assert "@OmniBlocks/coders" in result.notification_body
        assert "@unknown_user" in result.notification_body

    def test_reopen_authorization_check(self, guard):
        """Verify reopen permissions for authorized actors vs unauthorized actors."""
        unauthorized = Contributor(username="random_person", organization_member=False)
        authorized = Contributor(username="team_lead", organization_member=True, role="OWNER")
        pr = PullRequest(pr_number=15, title="Draft", description="WIP", author=unauthorized)

        assert guard.can_reopen(unauthorized) is False
        assert guard.can_reopen(authorized) is True

        denied, denied_msg = guard.evaluate_reopen_request(pr, unauthorized)
        assert denied is False
        assert "lacks required organizational authorization" in denied_msg

        allowed, allowed_msg = guard.evaluate_reopen_request(pr, authorized)
        assert allowed is True
        assert "successfully validated and reopened" in allowed_msg


class TestHumorAnalysisEngine:
    """Tests for HumorAnalysisEngine diff analysis and humor policy decisions."""

    @pytest.fixture
    def engine(self):
        """Fixture providing a fresh HumorAnalysisEngine instance."""
        return HumorAnalysisEngine()

    def test_extract_markers(self, engine):
        """Verify extraction of humor lexicon tokens."""
        text = "This is a funny joke about rubber duck and haha puns."
        markers = engine.extract_markers(text)
        assert "funny" in markers
        assert "joke" in markers
        assert "rubber duck" in markers
        assert "haha" in markers
        assert "puns" in markers

    def test_detect_intent(self, engine):
        """Verify intent detection in titles and text."""
        remove_title = "Refactor: remove humor and clean up jokes"
        add_title = "Feature: add funny jokes and sprinkle humor"
        neutral_title = "Fix typo in documentation"

        rem_flag1, add_flag1 = engine.detect_intent(remove_title)
        assert rem_flag1 is True
        assert add_flag1 is False

        rem_flag2, add_flag2 = engine.detect_intent(add_title)
        assert rem_flag2 is False
        assert add_flag2 is True

        rem_flag3, add_flag3 = engine.detect_intent(neutral_title)
        assert rem_flag3 is False
        assert add_flag3 is False

    def test_diff_adding_humor(self, engine):
        """Verify diff analysis when adding comedy."""
        diff = (
            "--- a/calculator.py\n"
            "+++ b/calculator.py\n"
            "@@ -10,3 +10,4 @@\n"
            " def add(a, b):\n"
            "+    # why did the rubber duck cross the road? haha\n"
            "+    print('hilarious funny joke')\n"
            "     return a + b\n"
        )
        analysis = engine.analyze_diff(diff)
        assert analysis.humor_classification == HumorClassification.HUMOR_ADDED
        assert analysis.humor_score_delta > 0
        assert len(analysis.added_markers) >= 3

    def test_diff_removing_humor(self, engine):
        """Verify diff analysis when stripping comedy."""
        diff = (
            "--- a/calculator.py\n"
            "+++ b/calculator.py\n"
            "@@ -10,4 +10,3 @@\n"
            " def add(a, b):\n"
            "-    # rubber duck haha funny joke\n"
            "     return a + b\n"
        )
        analysis = engine.analyze_diff(diff)
        assert analysis.humor_classification == HumorClassification.HUMOR_REMOVED
        assert analysis.humor_score_delta < 0
        assert len(analysis.removed_markers) >= 3

    def test_evaluate_pr_rejects_humor_removal(self, engine):
        """Verify PR attempting to remove humor is rejected."""
        diff = (
            "--- a/jokes.py\n"
            "+++ b/jokes.py\n"
            "@@ -1,4 +1,2 @@\n"
            "-def tell_joke():\n"
            "-    return 'haha funny pun'\n"
        )
        pr = PullRequest(
            pr_number=20,
            title="Clean up: remove jokes",
            description="Removing unnecessary humor from codebase",
            author=Contributor(username="serious_dev", organization_member=True),
            diff=diff,
        )
        verdict = engine.evaluate_pull_request(pr)
        assert verdict.action == PRAction.REQUEST_CHANGES
        assert verdict.classification == HumorClassification.HUMOR_REMOVED
        assert verdict.status_state == "failure"
        assert "REJECTED" in verdict.review_comment

    def test_evaluate_pr_approves_humor_addition(self, engine):
        """Verify PR introducing humor is accepted."""
        diff = (
            "--- a/bot.py\n"
            "+++ b/bot.py\n"
            "@@ -1,2 +1,4 @@\n"
            "+# rubber duck easter egg haha\n"
            "+print('funny joke')\n"
        )
        pr = PullRequest(
            pr_number=21,
            title="Inject comic relief",
            description="Adding hilarious puns",
            author=Contributor(username="joker", organization_member=True),
            diff=diff,
        )
        verdict = engine.evaluate_pull_request(pr)
        assert verdict.action == PRAction.APPROVE
        assert verdict.classification == HumorClassification.HUMOR_ADDED
        assert verdict.status_state == "success"
        assert "ACCEPTED" in verdict.review_comment

    def test_evaluate_pr_neutral(self, engine):
        """Verify neutral PR proceeds without humor judgment."""
        diff = (
            "--- a/math.py\n"
            "+++ b/math.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-x = 1\n"
            "+x = 2\n"
        )
        pr = PullRequest(
            pr_number=22,
            title="Bump integer",
            description="Increment x",
            author=Contributor(username="coder", organization_member=True),
            diff=diff,
        )
        verdict = engine.evaluate_pull_request(pr)
        assert verdict.action == PRAction.CONTINUE_REVIEW
        assert verdict.classification == HumorClassification.NEUTRAL
        assert verdict.status_state == "success"


class TestBoxySettlementEngine:
    """Tests for settlement calculations, cryptocurrency quotes, and address validation."""

    def test_contributor_ratio_tiers(self):
        """Verify contributor split ratio by tier."""
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("40")) == Decimal("0.95")
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("100")) == Decimal("0.92")
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("200")) == Decimal("0.92")
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("300")) == Decimal("0.90")
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("750")) == Decimal("0.87")
        assert BoxySettlementEngine.get_contributor_ratio(Decimal("2000")) == Decimal("0.85")

    def test_address_validators(self):
        """Verify address validation for EVM and Stellar networks."""
        evm_valid = "0xdEF1aeE7055cE03c808d3feefb08B18bbC8596E9"
        assert BoxySettlementEngine.validate_evm_address(evm_valid) is True
        assert BoxySettlementEngine.validate_evm_address("0x1234") is False
        assert BoxySettlementEngine.validate_evm_address("") is False

        stellar_valid = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
        assert BoxySettlementEngine.validate_stellar_address(stellar_valid) is True
        assert BoxySettlementEngine.validate_stellar_address("GSHORT") is False
        assert BoxySettlementEngine.validate_stellar_address("") is False

    def test_issue_1573_quotes_accuracy(self):
        """Verify exact mathematical quotes for Issue #1573 reward levels."""
        base_q, real_q, bonus_q = BoxySettlementEngine.calculate_issue_1573_quotes()

        assert base_q.nominal_usd == Decimal("100.00")
        assert base_q.coin_reward == Decimal("125.0000")
        assert base_q.contributor_ratio == Decimal("0.92")
        assert base_q.contributor_coins == Decimal("115.0000")
        assert base_q.net_cash_payout_usd == Decimal("82.80")
        assert base_q.platform_fee_usd == Decimal("17.20")

        assert real_q.nominal_usd == Decimal("200.00")
        assert real_q.coin_reward == Decimal("250.0000")
        assert real_q.contributor_ratio == Decimal("0.92")
        assert real_q.contributor_coins == Decimal("230.0000")
        assert real_q.net_cash_payout_usd == Decimal("165.60")
        assert real_q.platform_fee_usd == Decimal("34.40")

        assert bonus_q.nominal_usd == Decimal("300.00")
        assert bonus_q.coin_reward == Decimal("375.0000")
        assert bonus_q.contributor_ratio == Decimal("0.90")
        assert bonus_q.contributor_coins == Decimal("337.5000")
        assert bonus_q.net_cash_payout_usd == Decimal("243.00")
        assert bonus_q.platform_fee_usd == Decimal("57.00")

    def test_pppdud_disclaimer(self):
        """Verify PPPDUD joke token disclaimer evaluation evaluates to 0 USD value."""
        quote = BoxySettlementEngine.calculate_settlement(Decimal("200.00"), is_pppdud=True)
        assert quote.ppp_dud_amount == Decimal("200.00")
        assert quote.ppp_dud_value_usd == Decimal("0.00")


class TestBoxyReviewBot:
    """Integration tests for the complete Boxy Review Bot pipeline."""

    @pytest.fixture
    def bot(self):
        """Fixture providing a configured BoxyReviewBot instance."""
        wm = WhitelistManager(["approved_user"])
        return BoxyReviewBot(whitelist_manager=wm)

    def test_pipeline_closes_stranger_pr(self, bot):
        """Verify external contributor is gated and close payload formatted."""
        pr = PullRequest(
            pr_number=50,
            title="Random submission",
            description="Testing gate",
            author=Contributor(username="outsider", organization_member=False),
        )
        verdict = bot.evaluate_pull_request(pr)
        assert verdict.final_action == PRAction.CLOSE
        assert verdict.humor_result is None

        close_payload = bot.build_github_close_payload(verdict)
        assert close_payload["state"] == "closed"
        assert "@OmniBlocks/coders" in close_payload["comment"]

        status_payload = bot.build_github_status_payload(verdict)
        assert status_payload["state"] == "failure"
        assert status_payload["context"] == "boxy/authorization-gate"

    def test_pipeline_accepts_humor_from_whitelisted_user(self, bot):
        """Verify whitelisted user adding humor receives PR approval."""
        diff = (
            "--- a/feature.py\n"
            "+++ b/feature.py\n"
            "@@ -1,2 +1,3 @@\n"
            "+# rubber duck funny joke haha\n"
        )
        pr = PullRequest(
            pr_number=51,
            title="Add comedy",
            description="Injecting humor",
            author=Contributor(username="approved_user", organization_member=False),
            diff=diff,
        )
        verdict = bot.evaluate_pull_request(pr)
        assert verdict.final_action == PRAction.APPROVE

        review_payload = bot.build_github_review_payload(verdict)
        assert review_payload["event"] == "APPROVE"
        assert "ACCEPTED" in review_payload["body"]

        status_payload = bot.build_github_status_payload(verdict)
        assert status_payload["state"] == "success"
        assert status_payload["context"] == "boxy/humor-policy"

    def test_pipeline_rejects_humor_removal_from_member(self, bot):
        """Verify organization member stripping humor has changes requested."""
        diff = (
            "--- a/feature.py\n"
            "+++ b/feature.py\n"
            "@@ -1,3 +1,2 @@\n"
            "-# rubber duck funny joke haha\n"
        )
        pr = PullRequest(
            pr_number=52,
            title="Remove humor",
            description="Stripping jokes",
            author=Contributor(username="member_dev", organization_member=True),
            diff=diff,
        )
        verdict = bot.evaluate_pull_request(pr)
        assert verdict.final_action == PRAction.REQUEST_CHANGES

        review_payload = bot.build_github_review_payload(verdict)
        assert review_payload["event"] == "REQUEST_CHANGES"
        assert "REJECTED" in review_payload["body"]

        status_payload = bot.build_github_status_payload(verdict)
        assert status_payload["state"] == "failure"
        assert status_payload["context"] == "boxy/humor-policy"

    def test_reopen_handler(self, bot):
        """Verify bot handle_reopen_request mutates PR state when authorized."""
        pr = PullRequest(
            pr_number=53,
            title="Closed PR",
            description="Pending triage",
            author=Contributor(username="outsider", organization_member=False),
            state="closed",
        )
        owner = Contributor(username="boss", organization_member=True, role="OWNER")
        success, msg = bot.handle_reopen_request(pr, owner)
        assert success is True
        assert pr.state == "open"
        assert "successfully validated and reopened" in msg

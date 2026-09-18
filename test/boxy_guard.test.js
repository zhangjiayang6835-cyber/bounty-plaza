/**
 * @fileoverview Test suite for Boxy PR Guard and Review Bot (Node.js runtime).
 */

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const {
  MembershipStatus,
  PRAction,
  HumorClassification,
  Contributor,
  PullRequest,
  WhitelistManager,
  PreemptiveGuard,
  HumorAnalysisEngine,
  BoxySettlementEngine,
  BoxyReviewBot,
} = require("../src/boxy_guard.js");

function runAllTests() {
  const tempDir = path.join(__dirname, "tmp");
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

  const whitelistFile = path.join(tempDir, "test_whitelist.json");
  if (fs.existsSync(whitelistFile)) {
    fs.unlinkSync(whitelistFile);
  }

  const wm = new WhitelistManager(["alice", "bob"], whitelistFile);
  assert.strictEqual(wm.isWhitelisted("alice"), true);
  assert.strictEqual(wm.isWhitelisted("Bob"), true);
  assert.strictEqual(wm.isWhitelisted("@Alice"), true);
  assert.strictEqual(wm.isWhitelisted("charlie"), false);

  assert.strictEqual(wm.addUser("Charlie"), true);
  assert.strictEqual(wm.addUser("charlie"), false);
  assert.strictEqual(wm.isWhitelisted("charlie"), true);

  assert.strictEqual(wm.removeUser("bob"), true);
  assert.strictEqual(wm.removeUser("bob"), false);
  assert.strictEqual(wm.isWhitelisted("bob"), false);

  const reloadedWm = new WhitelistManager([], whitelistFile);
  assert.strictEqual(reloadedWm.isWhitelisted("alice"), true);
  assert.strictEqual(reloadedWm.isWhitelisted("charlie"), true);
  assert.strictEqual(reloadedWm.isWhitelisted("bob"), false);

  reloadedWm.clear();
  assert.strictEqual(reloadedWm.count(), 0);

  const guard = new PreemptiveGuard(new WhitelistManager(["trusted_coder"]), "OmniBlocks", "@OmniBlocks/coders");

  const botPr = new PullRequest(101, "Automated bump", "deps update", new Contributor("dependabot[bot]", false, "NONE", true));
  const botResult = guard.checkPullRequest(botPr);
  assert.strictEqual(botResult.shouldClose, false);
  assert.strictEqual(botResult.authorStatus, MembershipStatus.BOT);

  const memberPr = new PullRequest(102, "Core feature", "impl", new Contributor("lead_dev", true, "MEMBER", false));
  const memberResult = guard.checkPullRequest(memberPr);
  assert.strictEqual(memberResult.shouldClose, false);
  assert.strictEqual(memberResult.authorStatus, MembershipStatus.ORGANIZATION_MEMBER);

  const whitelistedPr = new PullRequest(103, "External patch", "fix", new Contributor("trusted_coder", false, "NONE", false));
  const whitelistedResult = guard.checkPullRequest(whitelistedPr);
  assert.strictEqual(whitelistedResult.shouldClose, false);
  assert.strictEqual(whitelistedResult.authorStatus, MembershipStatus.WHITELISTED);

  const strangerPr = new PullRequest(104, "Spam PR", "changes", new Contributor("unauthorized_user", false, "NONE", false));
  const strangerResult = guard.checkPullRequest(strangerPr);
  assert.strictEqual(strangerResult.shouldClose, true);
  assert.strictEqual(strangerResult.authorStatus, MembershipStatus.EXTERNAL_CONTRIBUTOR);
  assert.strictEqual(strangerResult.targetRolePing, "@OmniBlocks/coders");
  assert.ok(strangerResult.notificationBody.includes("@OmniBlocks/coders"));
  assert.ok(strangerResult.notificationBody.includes("@unauthorized_user"));

  const nonMemberActor = new Contributor("random_person", false, "NONE", false);
  const memberActor = new Contributor("maintainer", true, "COLLABORATOR", false);
  assert.strictEqual(guard.canReopen(nonMemberActor), false);
  assert.strictEqual(guard.canReopen(memberActor), true);

  const reopenFail = guard.evaluateReopenRequest(strangerPr, nonMemberActor);
  assert.strictEqual(reopenFail.approved, false);
  const reopenPass = guard.evaluateReopenRequest(strangerPr, memberActor);
  assert.strictEqual(reopenPass.approved, true);

  const humor = new HumorAnalysisEngine();

  const jokeDiff = [
    "--- a/file.py",
    "+++ b/file.py",
    "@@ -1,3 +1,4 @@",
    " def get_answer():",
    "+    # rubber duck said 42 haha",
    "+    return 'funny joke'",
  ].join("\n");

  const diffResult1 = humor.analyzeDiff(jokeDiff);
  assert.strictEqual(diffResult1.humorClassification, HumorClassification.HUMOR_ADDED);
  assert.ok(diffResult1.humorScoreDelta > 0);

  const humorPr = new PullRequest(201, "Add comic relief", "Injecting jokes into comments", new Contributor("comedian", true, "MEMBER"), "open", jokeDiff);
  const humorVerdict = humor.evaluatePullRequest(humorPr);
  assert.strictEqual(humorVerdict.action, PRAction.APPROVE);
  assert.strictEqual(humorVerdict.statusState, "success");

  const stripDiff = [
    "--- a/file.py",
    "+++ b/file.py",
    "@@ -1,4 +1,3 @@",
    "-    # rubber duck said 42 haha funny joke",
    "+    return 42",
  ].join("\n");

  const stripPr = new PullRequest(202, "Remove jokes and puns", "Sanitize funny comments", new Contributor("serious_dev", true, "MEMBER"), "open", stripDiff);
  const stripVerdict = humor.evaluatePullRequest(stripPr);
  assert.strictEqual(stripVerdict.action, PRAction.REQUEST_CHANGES);
  assert.strictEqual(stripVerdict.statusState, "failure");

  const neutralDiff = [
    "--- a/math.py",
    "+++ b/math.py",
    "@@ -1,2 +1,2 @@",
    "-x = 1",
    "+x = 2",
  ].join("\n");
  const neutralPr = new PullRequest(203, "Refactor variable", "update value", new Contributor("coder", true, "MEMBER"), "open", neutralDiff);
  const neutralVerdict = humor.evaluatePullRequest(neutralPr);
  assert.strictEqual(neutralVerdict.action, PRAction.CONTINUE_REVIEW);

  assert.strictEqual(BoxySettlementEngine.getContributorRatio(40), 0.95);
  assert.strictEqual(BoxySettlementEngine.getContributorRatio(100), 0.92);
  assert.strictEqual(BoxySettlementEngine.getContributorRatio(200), 0.92);
  assert.strictEqual(BoxySettlementEngine.getContributorRatio(300), 0.90);
  assert.strictEqual(BoxySettlementEngine.getContributorRatio(1500), 0.85);

  assert.strictEqual(BoxySettlementEngine.validateEvmAddress("0xdEF1aeE7055cE03c808d3feefb08B18bbC8596E9"), true);
  assert.strictEqual(BoxySettlementEngine.validateEvmAddress("0xinvalid"), false);
  assert.strictEqual(BoxySettlementEngine.validateStellarAddress("GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"), true);
  assert.strictEqual(BoxySettlementEngine.validateStellarAddress("invalid_stellar"), false);

  const quotes = BoxySettlementEngine.calculateIssue1573Quotes();
  assert.strictEqual(quotes.baseQuote.nominalUsd, 100);
  assert.strictEqual(quotes.baseQuote.coinReward, 125);
  assert.strictEqual(quotes.baseQuote.contributorCoins, 115);
  assert.strictEqual(quotes.baseQuote.netCashPayoutUsd, 82.80);
  assert.strictEqual(quotes.baseQuote.platformFeeUsd, 17.20);

  assert.strictEqual(quotes.realQuote.nominalUsd, 200);
  assert.strictEqual(quotes.realQuote.coinReward, 250);
  assert.strictEqual(quotes.realQuote.contributorCoins, 230);
  assert.strictEqual(quotes.realQuote.netCashPayoutUsd, 165.60);
  assert.strictEqual(quotes.realQuote.platformFeeUsd, 34.40);

  assert.strictEqual(quotes.bonusQuote.nominalUsd, 300);
  assert.strictEqual(quotes.bonusQuote.coinReward, 375);
  assert.strictEqual(quotes.bonusQuote.contributorCoins, 337.5);
  assert.strictEqual(quotes.bonusQuote.netCashPayoutUsd, 243.00);
  assert.strictEqual(quotes.bonusQuote.platformFeeUsd, 57.00);

  const pppdudQuote = BoxySettlementEngine.calculateSettlement(200, { isPppdud: true });
  assert.strictEqual(pppdudQuote.pppDudValueUsd, 0.0);

  const bot = new BoxyReviewBot(new WhitelistManager(["trusted_bot_user"]));

  const externalVerdict = bot.evaluatePullRequest(strangerPr);
  assert.strictEqual(externalVerdict.finalAction, PRAction.CLOSE);
  const closePayload = bot.buildGithubClosePayload(externalVerdict);
  assert.strictEqual(closePayload.state, "closed");

  const humorAddPr = new PullRequest(301, "Add funny easter egg", "puns inside", new Contributor("trusted_bot_user", false, "NONE"), "open", jokeDiff);
  const approvedVerdict = bot.evaluatePullRequest(humorAddPr);
  assert.strictEqual(approvedVerdict.finalAction, PRAction.APPROVE);
  const reviewPayload = bot.buildGithubReviewPayload(approvedVerdict);
  assert.strictEqual(reviewPayload.event, "APPROVE");

  const stripAuthor = new Contributor("trusted_bot_user", false, "NONE");
  const humorStripPr = new PullRequest(302, "Clean jokes", "strip humor", stripAuthor, "open", stripDiff);
  const rejectVerdict = bot.evaluatePullRequest(humorStripPr);
  assert.strictEqual(rejectVerdict.finalAction, PRAction.REQUEST_CHANGES);
  const rejectPayload = bot.buildGithubReviewPayload(rejectVerdict);
  assert.strictEqual(rejectPayload.event, "REQUEST_CHANGES");

  const reopenResult = bot.handleReopenRequest(strangerPr, memberActor);
  assert.strictEqual(reopenResult.success, true);
  assert.strictEqual(strangerPr.state, "open");

  if (fs.existsSync(whitelistFile)) {
    fs.unlinkSync(whitelistFile);
  }
  if (fs.existsSync(tempDir)) {
    fs.rmdirSync(tempDir);
  }

  process.stdout.write("All Node.js Boxy Guard tests passed successfully.\n");
}

runAllTests();

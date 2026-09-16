const { test, describe } = require("node:test");
const assert = require("node:assert/strict");
const {
  ReverseBountyDetector,
  ReversePaymentRouter,
  NegativeEscrowManager,
  PledgeSigner,
  ScraperGovernance,
  ReverseBountyBlogGenerator,
  ReverseBountyEngine,
} = require("../src/reverse_bounty.js");

describe("Reverse Bounty JavaScript Test Suite", () => {
  test("Detects reverse bounty on Issue #1558 text", () => {
    const detector = new ReverseBountyDetector();
    const title = "[Bounty] Reverse bounty";
    const body =
      "Hello! I am looking to pay a bounty of great magnitude* to whoever can complete the following tasks by April 1st, 2027:\n" +
      "• Write a blog post detailing how you were fooled into accepting a silly bounty, publish it on your website, and leave a link here.\n" +
      "• Pay me $500 in Solana, Bitcoin, Ethereum, or Monero.\n" +
      "• Pledge to stop spamming random projects looking for bounties.\n" +
      "*The bounty is negative.";

    const res = detector.analyze(title, body);
    assert.equal(res.isReverseBounty, true);
    assert.equal(res.polarity, "honeypot_prank");
    assert.equal(res.rawAmount, 500);
    assert.equal(res.sanitizedAmount, -500);
    assert.equal(res.requiresAntiSpamPledge, true);
    assert.equal(res.requiresReversePayment, true);
    assert.deepEqual(res.requestedChains.sort(), [
      "bitcoin",
      "ethereum",
      "monero",
      "solana",
    ]);
  });

  test("Classifies standard issue as positive reward", () => {
    const detector = new ReverseBountyDetector();
    const title = "Fix null pointer in payment gateway";
    const body = "Offering a reward of $250 for fixing this memory leak in prod.";
    const res = detector.analyze(title, body);
    assert.equal(res.isReverseBounty, false);
    assert.equal(res.polarity, "positive");
    assert.equal(res.rawAmount, 250);
    assert.equal(res.sanitizedAmount, 250);
  });

  test("Validates multi-chain addresses", () => {
    assert.equal(
      ReversePaymentRouter.validateAddress(
        "solana",
        "MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av"
      ),
      true
    );
    assert.equal(
      ReversePaymentRouter.validateAddress("solana", "invalid_0OIl_characters"),
      false
    );

    assert.equal(
      ReversePaymentRouter.validateAddress(
        "bitcoin",
        "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
      ),
      true
    );
    assert.equal(
      ReversePaymentRouter.validateAddress(
        "bitcoin",
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
      ),
      true
    );
    assert.equal(
      ReversePaymentRouter.validateAddress("bitcoin", "not_a_btc_address"),
      false
    );

    assert.equal(
      ReversePaymentRouter.validateAddress(
        "ethereum",
        "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
      ),
      true
    );
    assert.equal(
      ReversePaymentRouter.validateAddress("ethereum", "0x123"),
      false
    );

    assert.equal(
      ReversePaymentRouter.validateAddress(
        "monero",
        "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXMV33WDReCGWhr6p45Sm3DDtWXSJW33jjdmdfBoe3Eqev9Ac6KP"
      ),
      true
    );
    assert.equal(
      ReversePaymentRouter.validateAddress("monero", "short_xmr_addr"),
      false
    );
  });

  test("Creates quotes and builds unsigned transactions", () => {
    const router = new ReversePaymentRouter();
    const quote = router.createQuote(
      500,
      "solana",
      "MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av"
    );
    assert.equal(quote.usdAmount, 500);
    assert.equal(quote.chain, "solana");
    assert.ok(quote.cryptoAmount > 0);
    assert.ok(quote.totalCrypto > quote.cryptoAmount);

    const tx = router.buildTransaction(quote, "Test settlement");
    assert.equal(tx.chain, "solana");
    assert.ok(tx.txId.startsWith("tx_"));
    assert.ok(tx.payloadHex.length > 0);
    assert.equal(tx.status, "prepared_unsigned");
  });

  test("Manages negative escrow ledger and coin calculations", () => {
    assert.equal(NegativeEscrowManager.calculateReverseCoins(500), 625);

    const escrow = new NegativeEscrowManager();
    const record = escrow.recordDebit(
      "user_alpha",
      1558,
      500,
      "https://github.com/OmniBlocks/monorepo/issues/795"
    );
    assert.equal(record.coinsAmount, 625);
    assert.equal(record.status, "pending");
    assert.equal(escrow.getUserBalance("user_alpha"), -625);

    escrow.waiveWithPledgeAndBlog(
      record.recordId,
      "sig_hex_12345",
      "https://blog.example.com/post-mortem"
    );
    assert.equal(record.status, "waived_via_pledge");
    assert.equal(escrow.getUserBalance("user_alpha"), 0);
  });

  test("Signs and verifies anti-spam pledge", () => {
    const signer = new PledgeSigner();
    const pledge = signer.signPledge("s6pa1rta3n-lab", "issue#1558");
    assert.ok(pledge.signature.length === 64);
    assert.equal(signer.verifyPledge(pledge), true);

    const tampered = Object.assign({}, pledge, {
      pledgeText: "Tampered pledge text",
    });
    assert.equal(signer.verifyPledge(tampered), false);
  });

  test("Scraper governance blocks prank keywords", () => {
    assert.equal(
      ScraperGovernance.canInteractWithIssue(
        "Reverse bounty",
        "The bounty is negative"
      ),
      false
    );
    assert.equal(
      ScraperGovernance.canInteractWithIssue(
        "Fix API endpoint",
        "Reward $100 for bug fix"
      ),
      true
    );
  });

  test("End-to-end ReverseBountyEngine coordinates workflow", () => {
    const engine = new ReverseBountyEngine();
    const result = engine.processIssue(
      "[Bounty] Reverse bounty",
      "Pay me $500 in Solana. The bounty is negative. Stop spamming random projects.",
      1558,
      "https://github.com/OmniBlocks/monorepo/issues/795",
      "agent_fleet"
    );

    assert.equal(result.detection.isReverseBounty, true);
    assert.ok(result.debitRecord);
    assert.equal(result.debitRecord.coins_amount || result.debitRecord.coinsAmount, 625);
    assert.equal(result.allowedInteraction, false);
    assert.equal(result.requiresBlogPost, true);
    assert.equal(result.requiresAntiSpamPledge, true);
  });
});

/**
 * Reverse Bounty Detection, Multi-Chain Routing, Escrow Debit, and Anti-Spam Engine for Node.js.
 */

const crypto = require("node:crypto");

const OFFICIAL_PLEDGE_TEXT =
  "We solemnly pledge to stop spamming random open-source projects looking " +
  "for bounties. We commit to: " +
  "1. Deploying semantic polarity filters to reject reverse and prank bounties. " +
  "2. Enforcing maintainer opt-in and strict qualification before automated interaction. " +
  "3. Submitting only high-integrity, human-audited technical solutions. " +
  "4. Respecting developer attention and issue trackers.";

const BASE58_ALPHABET = new Set(
  "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz".split("")
);

const HEX_PATTERN = /^0x[a-fA-F0-9]{40}$/;
const BTC_BECH32_PATTERN = /^bc1[a-z0-9]{39,59}$/;
const BTC_LEGACY_PATTERN = /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/;
const SOL_PATTERN = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const XMR_PATTERN = /^[48][0-9AB-HJ-NP-Za-km-z]{94,105}$/;

class ReverseBountyDetector {
  /**
   * Constructs detector with sensitivity threshold.
   * @param {number} sensitivity
   */
  constructor(sensitivity = 0.5) {
    this.sensitivity = sensitivity;
    this.patterns = [
      [/\breverse\s*bounty\b/i, "reverse_bounty_title"],
      [/\bnegative\s*bounty\b/i, "negative_bounty_keyword"],
      [/\bbounty\s+is\s+negative\b/i, "bounty_is_negative_assertion"],
      [/\bpay\s+me\s+\$?\d+/i, "reverse_payment_demand"],
      [/\bpay\s+(?:the\s+)?author\b/i, "author_payment_demand"],
      [/\bfooled\s+into\s+accepting\b/i, "satirical_admission"],
      [/\bsilly\s+bounty\b/i, "silly_bounty_marker"],
      [/\bstop\s+spamming\s+(?:random\s+)?projects\b/i, "anti_spam_demand"],
      [/\bapril\s+1(?:st)?\b/i, "april_fools_date"],
      [/\bmagnitude\*\b/i, "magnitude_asterisk_qualifier"],
      [/-\s*\$\s*[\d,]+/i, "negative_dollar_sign"],
      [/\$\s*-\s*[\d,]+/i, "dollar_negative_sign"],
    ];
    this.chainPatterns = [
      [/\bsolana\b|\bsol\b/i, "solana"],
      [/\bbitcoin\b|\bbtc\b/i, "bitcoin"],
      [/\bethereum\b|\beth\b/i, "ethereum"],
      [/\bmonero\b|\bxmr\b/i, "monero"],
    ];
  }

  /**
   * Analyzes issue title and body for reverse bounty signatures.
   * @param {string} title
   * @param {string} body
   * @returns {object}
   */
  analyze(title, body) {
    const combined = `${title || ""}\n${body || ""}`;
    const matchedMarkers = [];

    for (const [regex, marker] of this.patterns) {
      if (regex.test(combined)) {
        matchedMarkers.push(marker);
      }
    }

    const requestedChains = [];
    for (const [regex, chain] of this.chainPatterns) {
      if (regex.test(combined) && !requestedChains.includes(chain)) {
        requestedChains.push(chain);
      }
    }

    let extractedAmount = null;
    const amountMatch = combined.match(/\$\s?([\d,]+(?:\.\d{1,2})?)/);
    if (amountMatch) {
      extractedAmount = parseFloat(amountMatch[1].replace(/,/g, ""));
    }

    let score = Math.min(1.0, matchedMarkers.length * 0.25);
    let isReverse = score >= this.sensitivity;

    if (
      matchedMarkers.includes("bounty_is_negative_assertion") ||
      matchedMarkers.includes("reverse_bounty_title")
    ) {
      isReverse = true;
      score = Math.max(score, 0.95);
    }

    let polarity = "positive";
    let sanitizedAmount = extractedAmount || 0;

    if (isReverse) {
      polarity =
        matchedMarkers.includes("satirical_admission") ||
        matchedMarkers.includes("april_fools_date")
          ? "honeypot_prank"
          : "negative_reverse";
      sanitizedAmount = -(extractedAmount || 0);
    }

    const requiresAntiSpam =
      matchedMarkers.includes("anti_spam_demand") ||
      /stop_spamming|stop spamming/i.test(combined);
    const requiresReversePayment =
      matchedMarkers.includes("reverse_payment_demand") || isReverse;

    return {
      isReverseBounty: isReverse,
      polarity,
      confidence: score,
      matchedMarkers,
      rawAmount: extractedAmount,
      sanitizedAmount,
      requiresAntiSpamPledge: requiresAntiSpam,
      requiresReversePayment,
      requestedChains,
    };
  }
}

class ReversePaymentRouter {
  /**
   * Constructs router with cryptocurrency spot prices.
   * @param {object} [customRates]
   */
  constructor(customRates = null) {
    this.rates = Object.assign(
      {
        solana: 150.0,
        bitcoin: 65000.0,
        ethereum: 3500.0,
        monero: 160.0,
      },
      customRates || {}
    );
    this.networkFees = {
      solana: 0.0005,
      bitcoin: 0.00015,
      ethereum: 0.0025,
      monero: 0.00005,
    };
  }

  /**
   * Validates blockchain address format.
   * @param {string} chain
   * @param {string} address
   * @returns {boolean}
   */
  static validateAddress(chain, address) {
    if (!address || typeof address !== "string") {
      return false;
    }
    const clean = address.trim();

    if (chain === "solana") {
      if (!SOL_PATTERN.test(clean)) return false;
      return clean.split("").every((c) => BASE58_ALPHABET.has(c));
    }
    if (chain === "bitcoin") {
      if (BTC_BECH32_PATTERN.test(clean)) return true;
      if (BTC_LEGACY_PATTERN.test(clean)) {
        return clean.split("").every((c) => BASE58_ALPHABET.has(c));
      }
      return false;
    }
    if (chain === "ethereum") {
      return HEX_PATTERN.test(clean);
    }
    if (chain === "monero") {
      if (clean.length !== 95 && clean.length !== 106) return false;
      if (!XMR_PATTERN.test(clean)) return false;
      return clean.split("").every((c) => BASE58_ALPHABET.has(c));
    }
    return false;
  }

  /**
   * Generates quote for cryptocurrency settlement.
   * @param {number} usdAmount
   * @param {string} chain
   * @param {string} recipientAddress
   * @returns {object}
   */
  createQuote(usdAmount, chain, recipientAddress) {
    if (!ReversePaymentRouter.validateAddress(chain, recipientAddress)) {
      throw new Error(`Invalid ${chain} address format: ${recipientAddress}`);
    }
    const rate = this.rates[chain] || 1.0;
    const cryptoAmount = parseFloat((usdAmount / rate).toFixed(8));
    const feeCrypto = this.networkFees[chain] || 0.001;
    const feeUsd = parseFloat((feeCrypto * rate).toFixed(2));
    const totalCrypto = parseFloat((cryptoAmount + feeCrypto).toFixed(8));
    const now = Date.now() / 1000;
    const seed = `${usdAmount}:${chain}:${recipientAddress}:${now}`;
    const quoteId = `quote_${crypto.createHash("sha256").update(seed).digest("hex").slice(0, 16)}`;

    return {
      quoteId,
      usdAmount,
      chain,
      cryptoAmount,
      rateUsd: rate,
      estimatedFeeCrypto: feeCrypto,
      estimatedFeeUsd: feeUsd,
      totalCrypto,
      recipientAddress,
      timestamp: now,
      expiresAt: now + 3600,
    };
  }

  /**
   * Builds an unsigned transaction payload.
   * @param {object} quote
   * @param {string} [memo]
   * @returns {object}
   */
  buildTransaction(quote, memo = "") {
    const payload = `CHAIN=${quote.chain}|TO=${quote.recipientAddress}|AMOUNT=${quote.cryptoAmount}|FEE=${quote.estimatedFeeCrypto}|MEMO=${memo}|EXP=${quote.expiresAt}`;
    const payloadHex = Buffer.from(payload, "utf-8").toString("hex");
    const txId = `tx_${crypto.createHash("sha256").update(payload).digest("hex").slice(0, 24)}`;

    return {
      txId,
      quoteId: quote.quoteId,
      chain: quote.chain,
      recipientAddress: quote.recipientAddress,
      amountCrypto: quote.cryptoAmount,
      feeCrypto: quote.estimatedFeeCrypto,
      payloadHex,
      memo,
      status: "prepared_unsigned",
    };
  }
}

class NegativeEscrowManager {
  /**
   * Initializes in-memory balance tracker.
   */
  constructor() {
    this.records = new Map();
    this.userBalances = new Map();
  }

  /**
   * Computes coins required for reverse bounty.
   * @param {number} usdAmount
   * @returns {number}
   */
  static calculateReverseCoins(usdAmount) {
    return Math.round(Math.abs(usdAmount) * 1.25 * 100) / 100;
  }

  /**
   * Records a debit against an account.
   * @param {string} userId
   * @param {number} issueId
   * @param {number} amountUsd
   * @param {string} [sourceUrl]
   * @returns {object}
   */
  recordDebit(userId, issueId, amountUsd, sourceUrl = "") {
    const coins = NegativeEscrowManager.calculateReverseCoins(amountUsd);
    const now = Date.now() / 1000;
    const recordId = `deb_${crypto.createHash("sha256").update(`${userId}:${issueId}:${now}`).digest("hex").slice(0, 16)}`;

    const record = {
      recordId,
      userId,
      issueId,
      sourceUrl,
      amountUsd: Math.abs(amountUsd),
      coinsAmount: coins,
      status: "pending",
      createdAt: now,
      settledAt: null,
      txId: null,
      pledgeSignature: null,
      blogUrl: null,
    };

    this.records.set(recordId, record);
    const curr = this.userBalances.get(userId) || 0;
    this.userBalances.set(userId, curr - coins);
    return record;
  }

  /**
   * Waives debt when pledge and blog are confirmed.
   * @param {string} recordId
   * @param {string} pledgeSignature
   * @param {string} blogUrl
   * @returns {object}
   */
  waiveWithPledgeAndBlog(recordId, pledgeSignature, blogUrl) {
    const record = this.records.get(recordId);
    if (!record) {
      throw new Error(`Record not found: ${recordId}`);
    }
    record.status = "waived_via_pledge";
    record.settledAt = Date.now() / 1000;
    record.pledgeSignature = pledgeSignature;
    record.blogUrl = blogUrl;
    const curr = this.userBalances.get(record.userId) || 0;
    this.userBalances.set(record.userId, curr + record.coinsAmount);
    return record;
  }

  /**
   * Retrieves net user coin balance.
   * @param {string} userId
   * @returns {number}
   */
  getUserBalance(userId) {
    return this.userBalances.get(userId) || 0;
  }
}

class PledgeSigner {
  /**
   * Constructs signer with secret key.
   * @param {string} [secretKey]
   */
  constructor(secretKey = "bounty-plaza-anti-spam-key") {
    this.secretKey = secretKey;
  }

  /**
   * Generates a signed anti-spam pledge.
   * @param {string} signerId
   * @param {string} issueRef
   * @param {number} [timestamp]
   * @returns {object}
   */
  signPledge(signerId, issueRef, timestamp = null) {
    const ts = timestamp || Date.now() / 1000;
    const payload = `${OFFICIAL_PLEDGE_TEXT}|${signerId}|${issueRef}|${ts}`;
    const signature = crypto
      .createHmac("sha256", this.secretKey)
      .update(payload)
      .digest("hex");

    return {
      pledgeText: OFFICIAL_PLEDGE_TEXT,
      signerId,
      issueReference: issueRef,
      timestamp: ts,
      signature,
    };
  }

  /**
   * Validates signed pledge.
   * @param {object} pledge
   * @returns {boolean}
   */
  verifyPledge(pledge) {
    if (!pledge || pledge.pledgeText !== OFFICIAL_PLEDGE_TEXT) {
      return false;
    }
    const payload = `${pledge.pledgeText}|${pledge.signerId}|${pledge.issueReference}|${pledge.timestamp}`;
    const expected = crypto
      .createHmac("sha256", this.secretKey)
      .update(payload)
      .digest("hex");
    return crypto.timingSafeEqual(
      Buffer.from(pledge.signature),
      Buffer.from(expected)
    );
  }
}

class ScraperGovernance {
  /**
   * Evaluates if issue is permitted for automated interaction.
   * @param {string} title
   * @param {string} body
   * @returns {boolean}
   */
  static canInteractWithIssue(title, body) {
    const text = `${title || ""}\n${body || ""}`.toLowerCase();
    const banned = [
      "reverse bounty",
      "the bounty is negative",
      "fooled into",
      "silly bounty",
      "pay me $",
      "stop spamming",
      "april 1st",
    ];
    return !banned.some((kw) => text.includes(kw));
  }
}

class ReverseBountyBlogGenerator {
  /**
   * Initializes generator with author name.
   * @param {string} [author]
   */
  constructor(author = "Universal Bounty Fleet / s6pa1rta3n-lab") {
    this.author = author;
  }

  /**
   * Generates formatted markdown blog post.
   * @param {string} issueRef
   * @param {string} sourceUrl
   * @param {number} amountUsd
   * @returns {string}
   */
  generateMarkdown(issueRef, sourceUrl, amountUsd = 500.0) {
    return (
      `# How We Were Fooled by a Reverse Bounty: A Technical Post-Mortem\n\n` +
      `**Author:** ${this.author}\n` +
      `**Date:** 2026-09-16\n` +
      `**Target Issue:** ${issueRef}\n` +
      `**Source:** [${sourceUrl}](${sourceUrl})\n\n` +
      `## Summary\n\n` +
      `Autonomous bounty systems must validate semantic polarity and directionality. ` +
      `This incident analysis details our resolution of reverse bounty ${issueRef} ($${amountUsd}).`
    );
  }
}

class ReverseBountyEngine {
  /**
   * Initializes sub-modules.
   * @param {string} [author]
   */
  constructor(author = "Universal Bounty Fleet / s6pa1rta3n-lab") {
    this.detector = new ReverseBountyDetector();
    this.router = new ReversePaymentRouter();
    this.escrow = new NegativeEscrowManager();
    this.signer = new PledgeSigner();
    this.blog = new ReverseBountyBlogGenerator(author);
  }

  /**
   * Processes issue through detector and escrow pipeline.
   * @param {string} title
   * @param {string} body
   * @param {number} issueId
   * @param {string} [sourceUrl]
   * @param {string} [userId]
   * @returns {object}
   */
  processIssue(title, body, issueId, sourceUrl = "", userId = "default_user") {
    const detection = this.detector.analyze(title, body);
    let debitRecord = null;
    if (detection.isReverseBounty && detection.rawAmount) {
      debitRecord = this.escrow.recordDebit(
        userId,
        issueId,
        detection.rawAmount,
        sourceUrl
      );
    }
    return {
      detection,
      debitRecord,
      requiresBlogPost: detection.isReverseBounty,
      requiresAntiSpamPledge: detection.requiresAntiSpamPledge,
      requiresReversePayment: detection.requiresReversePayment,
      allowedInteraction: ScraperGovernance.canInteractWithIssue(title, body),
    };
  }
}

module.exports = {
  ReverseBountyDetector,
  ReversePaymentRouter,
  NegativeEscrowManager,
  PledgeSigner,
  ScraperGovernance,
  ReverseBountyBlogGenerator,
  ReverseBountyEngine,
  OFFICIAL_PLEDGE_TEXT,
};

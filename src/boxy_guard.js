/**
 * @fileoverview Boxy code review bot: Pre-emptive PR closing guard, humor review engine, and settlement runtime.
 */

const fs = require("fs");
const path = require("path");

const MembershipStatus = Object.freeze({
  ORGANIZATION_MEMBER: "ORGANIZATION_MEMBER",
  WHITELISTED: "WHITELISTED",
  EXTERNAL_CONTRIBUTOR: "EXTERNAL_CONTRIBUTOR",
  BOT: "BOT",
});

const PRAction = Object.freeze({
  CLOSE: "CLOSE",
  REQUEST_CHANGES: "REQUEST_CHANGES",
  APPROVE: "APPROVE",
  CONTINUE_REVIEW: "CONTINUE_REVIEW",
});

const HumorClassification = Object.freeze({
  HUMOR_ADDED: "HUMOR_ADDED",
  HUMOR_REMOVED: "HUMOR_REMOVED",
  NEUTRAL: "NEUTRAL",
});

const Currency = Object.freeze({
  BTC: "BTC",
  XMR: "XMR",
  SOL: "SOL",
  USD: "USD",
  EVM: "EVM",
  STELLAR: "STELLAR",
  PPPDUD: "PPPDUD",
});

/**
 * Contributor identity and role permissions.
 */
class Contributor {
  /**
   * @param {string} username
   * @param {boolean} [organizationMember=false]
   * @param {string} [role="NONE"]
   * @param {boolean} [isBot=false]
   */
  constructor(username, organizationMember = false, role = "NONE", isBot = false) {
    this.username = username;
    this.organizationMember = Boolean(organizationMember);
    this.role = role || "NONE";
    this.isBot = Boolean(isBot);
  }

  /**
   * Determine whether contributor is authorized to submit PRs without pre-emptive closure.
   * @param {boolean} isWhitelisted
   * @returns {boolean}
   */
  isAuthorized(isWhitelisted) {
    if (this.isBot) return true;
    if (this.organizationMember) return true;
    const roleUpper = (this.role || "").toUpperCase();
    if (["OWNER", "MEMBER", "COLLABORATOR"].includes(roleUpper)) return true;
    return Boolean(isWhitelisted);
  }
}

/**
 * Pull request metadata representation.
 */
class PullRequest {
  /**
   * @param {number} prNumber
   * @param {string} title
   * @param {string} description
   * @param {Contributor} author
   * @param {string} [state="open"]
   * @param {string} [diff=""]
   * @param {string[]} [labels=[]]
   * @param {string} [baseRef="main"]
   * @param {string} [headSha=""]
   */
  constructor(prNumber, title, description, author, state = "open", diff = "", labels = [], baseRef = "main", headSha = "") {
    this.prNumber = prNumber;
    this.title = title || "";
    this.description = description || "";
    this.author = author;
    this.state = state;
    this.diff = diff;
    this.labels = labels;
    this.baseRef = baseRef;
    this.headSha = headSha;
  }
}

/**
 * Whitelist manager for explicitly permitted contributors.
 */
class WhitelistManager {
  /**
   * @param {string[]} [initialUsers=[]]
   * @param {string} [storagePath=null]
   */
  constructor(initialUsers = [], storagePath = null) {
    this._whitelisted = new Set();
    this._storagePath = storagePath;

    if (Array.isArray(initialUsers)) {
      for (const u of initialUsers) {
        this.addUser(u);
      }
    }

    if (this._storagePath && fs.existsSync(this._storagePath)) {
      this.loadFromFile(this._storagePath);
    }
  }

  /**
   * @param {string} username
   * @returns {boolean}
   */
  addUser(username) {
    if (!username || typeof username !== "string") return false;
    const cleaned = username.trim().replace(/^@/, "").toLowerCase();
    if (!cleaned || this._whitelisted.has(cleaned)) return false;
    this._whitelisted.add(cleaned);
    if (this._storagePath) this.saveToFile(this._storagePath);
    return true;
  }

  /**
   * @param {string} username
   * @returns {boolean}
   */
  removeUser(username) {
    if (!username || typeof username !== "string") return false;
    const cleaned = username.trim().replace(/^@/, "").toLowerCase();
    if (!this._whitelisted.has(cleaned)) return false;
    this._whitelisted.delete(cleaned);
    if (this._storagePath) this.saveToFile(this._storagePath);
    return true;
  }

  /**
   * @param {string} username
   * @returns {boolean}
   */
  isWhitelisted(username) {
    if (!username || typeof username !== "string") return false;
    const cleaned = username.trim().replace(/^@/, "").toLowerCase();
    return this._whitelisted.has(cleaned);
  }

  /**
   * @returns {string[]}
   */
  getWhitelist() {
    return Array.from(this._whitelisted).sort();
  }

  /**
   * @returns {void}
   */
  clear() {
    this._whitelisted.clear();
    if (this._storagePath) this.saveToFile(this._storagePath);
  }

  /**
   * @returns {number}
   */
  count() {
    return this._whitelisted.size;
  }

  /**
   * @param {string} filePath
   * @returns {void}
   */
  saveToFile(filePath) {
    const dir = path.dirname(filePath);
    if (dir && !fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    const data = { whitelisted_users: this.getWhitelist() };
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  }

  /**
   * @param {string} filePath
   * @returns {void}
   */
  loadFromFile(filePath) {
    if (!fs.existsSync(filePath)) return;
    try {
      const raw = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(raw);
      if (data && Array.isArray(data.whitelisted_users)) {
        for (const u of data.whitelisted_users) {
          this.addUser(u);
        }
      }
    } catch (_) {
      // safe fallback
    }
  }
}

/**
 * Pre-emptive PR closing gate enforcing organization authorization.
 */
class PreemptiveGuard {
  /**
   * @param {WhitelistManager} [whitelistManager=null]
   * @param {string} [organization="OmniBlocks"]
   * @param {string} [pingTarget="@OmniBlocks/coders"]
   */
  constructor(whitelistManager = null, organization = "OmniBlocks", pingTarget = "@OmniBlocks/coders") {
    this.whitelist = whitelistManager || new WhitelistManager();
    this.organization = organization;
    this.pingTarget = pingTarget;
  }

  /**
   * @param {Contributor} contributor
   * @returns {string}
   */
  resolveMembershipStatus(contributor) {
    if (contributor.isBot || (contributor.username && contributor.username.endsWith("[bot]"))) {
      return MembershipStatus.BOT;
    }
    if (contributor.organizationMember) {
      return MembershipStatus.ORGANIZATION_MEMBER;
    }
    const roleUpper = (contributor.role || "").toUpperCase();
    if (["OWNER", "MEMBER", "COLLABORATOR"].includes(roleUpper)) {
      return MembershipStatus.ORGANIZATION_MEMBER;
    }
    if (this.whitelist.isWhitelisted(contributor.username)) {
      return MembershipStatus.WHITELISTED;
    }
    return MembershipStatus.EXTERNAL_CONTRIBUTOR;
  }

  /**
   * @param {PullRequest} pr
   * @returns {object}
   */
  checkPullRequest(pr) {
    const status = this.resolveMembershipStatus(pr.author);

    if (
      status === MembershipStatus.BOT ||
      status === MembershipStatus.ORGANIZATION_MEMBER ||
      status === MembershipStatus.WHITELISTED
    ) {
      return {
        shouldClose: false,
        authorStatus: status,
        targetRolePing: "",
        notificationBody: "",
        auditReason: `Contributor @${pr.author.username} authorized under tier ${status}.`,
      };
    }

    const notification =
      `Notice: Pull request #${pr.prNumber} by @${pr.author.username} has been pre-emptively closed.\n\n` +
      `Under the ${this.organization} security policy, pull requests from contributors outside the ` +
      `organization who are not on the explicit whitelist must be closed pending triage.\n\n` +
      `Paging ${this.pingTarget} to review contributor credentials and reopen this pull request ` +
      `before initiating automated code review.\n\n` +
      `Contributor: @${pr.author.username}\n` +
      `Status: Non-Member / Unlisted\n` +
      `Action Required: Team member verification and manual reopening.`;

    const auditReason =
      `Pre-emptive closure triggered for PR #${pr.prNumber}: @${pr.author.username} is an external ` +
      `contributor not present on the ${this.organization} whitelist.`;

    return {
      shouldClose: true,
      authorStatus: status,
      targetRolePing: this.pingTarget,
      notificationBody: notification,
      auditReason,
    };
  }

  /**
   * @param {Contributor} actor
   * @returns {boolean}
   */
  canReopen(actor) {
    if (actor.isBot) return false;
    if (actor.organizationMember) return true;
    const roleUpper = (actor.role || "").toUpperCase();
    return ["OWNER", "MEMBER", "COLLABORATOR"].includes(roleUpper);
  }

  /**
   * @param {PullRequest} pr
   * @param {Contributor} actor
   * @returns {{ approved: boolean, message: string }}
   */
  evaluateReopenRequest(pr, actor) {
    if (!this.canReopen(actor)) {
      return {
        approved: false,
        message:
          `Reopen rejected: @${actor.username} lacks required organizational authorization. ` +
          `Only members of ${this.organization} or repository maintainers may reopen pre-emptively closed PRs.`,
      };
    }
    return {
      approved: true,
      message:
        `Pull request #${pr.prNumber} successfully validated and reopened by @${actor.username} ` +
        `(${actor.role}). Automated code review pipeline is now unblocked.`,
    };
  }
}

/**
 * Humor detection and policy review engine.
 */
class HumorAnalysisEngine {
  constructor() {
    this.humorLexicon = [
      "joke", "pun", "puns", "haha", "hehe", "lol", "lmao", "rofl",
      "giggle", "snicker", "chuckle", "humor", "humour", "funny",
      "comedic", "hilarious", "wit", "witty", "easter egg", "rickroll",
      "skill issue", "rubber duck", "dad joke", "knock knock",
      "why did the", "spaghetti code", "facepalm", "leeroy",
      "all your base", "works on my machine", "feature not a bug",
      "famous last words", "more cowbell", "comic relief",
      "cat knocked down", "banana for scale", "potato", "clown",
    ];

    this.removeHumorPhrases = [
      "remove humor", "remove jokes", "delete pun", "delete puns",
      "remove puns", "clean up jokes", "strip humor", "remove comedic",
      "sanitize funny", "remove easter egg", "no jokes allowed",
      "remove sarcasm", "remove meme", "remove memes", "stop clowning",
      "humor removal", "remove all jokes", "eliminate humor",
    ];

    this.addHumorPhrases = [
      "add humor", "add joke", "add jokes", "add pun", "add puns",
      "add funny", "sprinkle humor", "make it funny", "comic relief",
      "add memes", "add meme", "humor injection", "more humor",
      "inject jokes", "funny easter egg",
    ];

    const escapedLexicon = this.humorLexicon.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    this._lexiconRegex = new RegExp(`\\b(${escapedLexicon.join("|")})\\b`, "gi");

    const escapedRemove = this.removeHumorPhrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    this._removeRegex = new RegExp(`(${escapedRemove.join("|")})`, "i");

    const escapedAdd = this.addHumorPhrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    this._addRegex = new RegExp(`(${escapedAdd.join("|")})`, "i");
  }

  /**
   * @param {string} text
   * @returns {string[]}
   */
  extractMarkers(text) {
    if (!text || typeof text !== "string") return [];
    const matches = text.match(this._lexiconRegex);
    if (!matches) return [];
    return matches.map((m) => m.toLowerCase());
  }

  /**
   * @param {string} text
   * @returns {{ attemptsRemove: boolean, attemptsAdd: boolean }}
   */
  detectIntent(text) {
    if (!text || typeof text !== "string") {
      return { attemptsRemove: false, attemptsAdd: false };
    }
    return {
      attemptsRemove: this._removeRegex.test(text),
      attemptsAdd: this._addRegex.test(text),
    };
  }

  /**
   * @param {string} diffText
   * @returns {object}
   */
  analyzeDiff(diffText) {
    if (!diffText || typeof diffText !== "string") {
      return {
        addedLines: 0,
        removedLines: 0,
        humorScoreDelta: 0,
        humorClassification: HumorClassification.NEUTRAL,
        addedMarkers: [],
        removedMarkers: [],
      };
    }

    let addedLines = 0;
    let removedLines = 0;
    const addedMarkers = [];
    const removedMarkers = [];

    const lines = diffText.split("\n");
    for (const line of lines) {
      if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
        continue;
      }
      if (line.startsWith("+")) {
        addedLines += 1;
        const markers = this.extractMarkers(line.slice(1));
        addedMarkers.push(...markers);
      } else if (line.startsWith("-")) {
        removedLines += 1;
        const markers = this.extractMarkers(line.slice(1));
        removedMarkers.push(...markers);
      }
    }

    const delta = addedMarkers.length - removedMarkers.length;
    let classification = HumorClassification.NEUTRAL;
    if (delta < 0) {
      classification = HumorClassification.HUMOR_REMOVED;
    } else if (delta > 0) {
      classification = HumorClassification.HUMOR_ADDED;
    }

    return {
      addedLines,
      removedLines,
      humorScoreDelta: delta,
      humorClassification: classification,
      addedMarkers,
      removedMarkers,
    };
  }

  /**
   * @param {PullRequest} pr
   * @returns {object}
   */
  evaluatePullRequest(pr) {
    const metadata = `${pr.title || ""}\n${pr.description || ""}`;
    const { attemptsRemove, attemptsAdd } = this.detectIntent(metadata);
    const diffAnalysis = this.analyzeDiff(pr.diff);

    let effectiveDelta = diffAnalysis.humorScoreDelta;
    if (attemptsRemove) effectiveDelta -= 10;
    if (attemptsAdd) effectiveDelta += 10;

    if (effectiveDelta < 0 || (attemptsRemove && !attemptsAdd)) {
      const comment =
        `Boxy Code Review Bot - Humor Policy Enforcement: REJECTED\n\n` +
        `Pull request #${pr.prNumber} attempts to remove humor from the repository. ` +
        `Under Boxy governance directives, humor and wit are essential project requirements.\n\n` +
        `Metrics:\n` +
        `- Humor delta: ${effectiveDelta}\n` +
        `- Humor tokens removed: ${diffAnalysis.removedMarkers.length}\n` +
        `- Removal intent detected: ${attemptsRemove ? "Yes" : "No"}\n\n` +
        `Resolution: Please preserve existing humor or introduce new comedic elements to pass review.`;

      return {
        action: PRAction.REQUEST_CHANGES,
        classification: HumorClassification.HUMOR_REMOVED,
        scoreDelta: effectiveDelta,
        reviewComment: comment,
        statusContext: "boxy/humor-policy",
        statusState: "failure",
      };
    }

    if (effectiveDelta > 0 || attemptsAdd) {
      const comment =
        `Boxy Code Review Bot - Humor Policy Enforcement: ACCEPTED\n\n` +
        `Pull request #${pr.prNumber} successfully introduces humor into the repository. ` +
        `Boxy appreciates your witty contributions to developer morale!\n\n` +
        `Metrics:\n` +
        `- Humor delta: +${effectiveDelta}\n` +
        `- Humor tokens added: ${diffAnalysis.addedMarkers.length}\n` +
        `- Addition intent detected: ${attemptsAdd ? "Yes" : "No"}\n\n` +
        `Verdict: Approved on humor merit.`;

      return {
        action: PRAction.APPROVE,
        classification: HumorClassification.HUMOR_ADDED,
        scoreDelta: effectiveDelta,
        reviewComment: comment,
        statusContext: "boxy/humor-policy",
        statusState: "success",
      };
    }

    return {
      action: PRAction.CONTINUE_REVIEW,
      classification: HumorClassification.NEUTRAL,
      scoreDelta: 0,
      reviewComment:
        `Boxy Code Review Bot - Humor Policy Enforcement: NEUTRAL\n\n` +
        `Pull request #${pr.prNumber} has a neutral humor score delta (0). ` +
        `Proceeding to standard code evaluation.`,
      statusContext: "boxy/humor-policy",
      statusState: "success",
    };
  }
}

/**
 * Financial settlement and payout calculation engine.
 */
class BoxySettlementEngine {
  static COIN_RATE = 1.25;
  static REDEMPTION_RATE = 0.72;
  static SATOSHIS_PER_BTC = 100000000;
  static DEFAULT_EVM_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89";
  static DEFAULT_STELLAR_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC";
  static DEFAULT_BTC_PRICE = 65000.0;
  static DEFAULT_XMR_PRICE = 150.0;
  static DEFAULT_SOL_PRICE = 140.0;

  /**
   * @param {number} usdAmount
   * @returns {number}
   */
  static getContributorRatio(usdAmount) {
    if (usdAmount < 50) return 0.95;
    if (usdAmount <= 200) return 0.92;
    if (usdAmount <= 500) return 0.90;
    if (usdAmount <= 1000) return 0.87;
    return 0.85;
  }

  /**
   * @param {string} address
   * @returns {boolean}
   */
  static validateEvmAddress(address) {
    if (!address || typeof address !== "string") return false;
    return /^0x[a-fA-F0-9]{40}$/.test(address.trim());
  }

  /**
   * @param {string} address
   * @returns {boolean}
   */
  static validateStellarAddress(address) {
    if (!address || typeof address !== "string") return false;
    return /^[GC][A-Z2-7]{55}$/.test(address.trim());
  }

  /**
   * @param {number} usdAmount
   * @param {object} [options={}]
   * @returns {object}
   */
  static calculateSettlement(usdAmount, options = {}) {
    const btcPrice = options.btcPrice || this.DEFAULT_BTC_PRICE;
    const xmrPrice = options.xmrPrice || this.DEFAULT_XMR_PRICE;
    const solPrice = options.solPrice || this.DEFAULT_SOL_PRICE;
    const evmAddress = options.evmAddress || this.DEFAULT_EVM_ADDRESS;
    const stellarAddress = options.stellarAddress || this.DEFAULT_STELLAR_ADDRESS;
    const isPppdud = Boolean(options.isPppdud);

    const nominalUsd = Number(usdAmount);
    const coinsTotal = Number((nominalUsd * this.COIN_RATE).toFixed(4));
    const contributorRatio = this.getContributorRatio(nominalUsd);
    const contributorCoins = Number((coinsTotal * contributorRatio).toFixed(4));
    const netCashPayoutUsd = Number((contributorCoins * this.REDEMPTION_RATE).toFixed(2));
    const platformFeeUsd = Number((nominalUsd - netCashPayoutUsd).toFixed(2));

    const btcAmount = Number((netCashPayoutUsd / btcPrice).toFixed(8));
    const satoshis = Math.round(btcAmount * this.SATOSHIS_PER_BTC);
    const xmrAmount = Number((netCashPayoutUsd / xmrPrice).toFixed(8));
    const solAmount = Number((netCashPayoutUsd / solPrice).toFixed(8));

    return {
      nominalUsd,
      realUsd: isPppdud ? 0.0 : nominalUsd,
      coinReward: coinsTotal,
      contributorRatio,
      contributorCoins,
      netCashPayoutUsd,
      platformFeeUsd,
      btcAmount,
      satoshis,
      xmrAmount,
      solAmount,
      evmAddress,
      stellarAddress,
      pppDudAmount: nominalUsd,
      pppDudValueUsd: isPppdud ? 0.0 : netCashPayoutUsd,
    };
  }

  /**
   * @returns {{ baseQuote: object, realQuote: object, bonusQuote: object }}
   */
  static calculateIssue1573Quotes() {
    return {
      baseQuote: this.calculateSettlement(100.0),
      realQuote: this.calculateSettlement(200.0),
      bonusQuote: this.calculateSettlement(300.0),
    };
  }
}

/**
 * Complete review bot orchestrator.
 */
class BoxyReviewBot {
  /**
   * @param {WhitelistManager} [whitelistManager=null]
   * @param {string} [organization="OmniBlocks"]
   * @param {string} [pingTarget="@OmniBlocks/coders"]
   */
  constructor(whitelistManager = null, organization = "OmniBlocks", pingTarget = "@OmniBlocks/coders") {
    this.whitelist = whitelistManager || new WhitelistManager();
    this.guard = new PreemptiveGuard(this.whitelist, organization, pingTarget);
    this.humorEngine = new HumorAnalysisEngine();
  }

  /**
   * @param {PullRequest} pr
   * @returns {object}
   */
  evaluatePullRequest(pr) {
    const preemptiveResult = this.guard.checkPullRequest(pr);

    if (preemptiveResult.shouldClose) {
      return {
        prNumber: pr.prNumber,
        preemptiveResult,
        humorResult: null,
        finalAction: PRAction.CLOSE,
        summaryMessage:
          `PR #${pr.prNumber} pre-emptively closed. Author @${pr.author.username} is not ` +
          `in organization nor whitelisted. Paging ${this.guard.pingTarget}.`,
      };
    }

    const humorResult = this.humorEngine.evaluatePullRequest(pr);
    let finalAction = PRAction.CONTINUE_REVIEW;
    let summary = `PR #${pr.prNumber} passed humor check. Proceeding to code evaluation.`;

    if (humorResult.action === PRAction.REQUEST_CHANGES) {
      finalAction = PRAction.REQUEST_CHANGES;
      summary = `PR #${pr.prNumber} review requested changes: PR attempts to remove humor from the codebase.`;
    } else if (humorResult.action === PRAction.APPROVE) {
      finalAction = PRAction.APPROVE;
      summary = `PR #${pr.prNumber} approved: PR successfully contributes humor to the codebase.`;
    }

    return {
      prNumber: pr.prNumber,
      preemptiveResult,
      humorResult,
      finalAction,
      summaryMessage: summary,
    };
  }

  /**
   * @param {PullRequest} pr
   * @param {Contributor} actor
   * @returns {{ success: boolean, message: string }}
   */
  handleReopenRequest(pr, actor) {
    const res = this.guard.evaluateReopenRequest(pr, actor);
    if (res.approved) {
      pr.state = "open";
    }
    return {
      success: res.approved,
      message: res.message,
    };
  }

  /**
   * @param {object} verdict
   * @returns {object}
   */
  buildGithubClosePayload(verdict) {
    return {
      state: "closed",
      state_reason: "not_planned",
      comment: verdict.preemptiveResult.notificationBody,
    };
  }

  /**
   * @param {object} verdict
   * @returns {object}
   */
  buildGithubReviewPayload(verdict) {
    if (!verdict.humorResult) {
      return {
        event: "COMMENT",
        body: verdict.preemptiveResult.notificationBody,
      };
    }
    let event = "COMMENT";
    if (verdict.finalAction === PRAction.APPROVE) event = "APPROVE";
    if (verdict.finalAction === PRAction.REQUEST_CHANGES) event = "REQUEST_CHANGES";
    return {
      event,
      body: verdict.humorResult.reviewComment,
    };
  }

  /**
   * @param {object} verdict
   * @returns {object}
   */
  buildGithubStatusPayload(verdict) {
    if (verdict.preemptiveResult.shouldClose) {
      return {
        state: "failure",
        context: "boxy/authorization-gate",
        description: "Pre-emptively closed: Author is not an org member or whitelisted.",
      };
    }
    if (verdict.humorResult) {
      return {
        state: verdict.humorResult.statusState,
        context: verdict.humorResult.statusContext,
        description:
          verdict.humorResult.statusState === "success"
            ? "Humor policy passed."
            : "Humor removal detected. Rejected.",
      };
    }
    return {
      state: "success",
      context: "boxy/gate",
      description: "All pre-flight checks passed.",
    };
  }
}

module.exports = {
  MembershipStatus,
  PRAction,
  HumorClassification,
  Currency,
  Contributor,
  PullRequest,
  WhitelistManager,
  PreemptiveGuard,
  HumorAnalysisEngine,
  BoxySettlementEngine,
  BoxyReviewBot,
};

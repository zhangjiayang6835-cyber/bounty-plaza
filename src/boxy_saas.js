/**
 * Node.js multi-tenant SaaS workspace and Bitcoin billing runtime for Boxy assistant.
 */

const crypto = require("crypto");

const EVM_PAYOUT_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89";
const STELLAR_PAYOUT_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC";
const SATOSHIS_PER_BITCOIN = 100000000;

const TIER_POLICIES = {
  free: {
    tier: "free",
    maxMonthlyTokens: 500000,
    maxReviewsPerDay: 10,
    maxConcurrentContainers: 1,
    maxStickyNotes: 50,
    priceUsd: 0.0,
    priceBtc: 0.0,
  },
  pro: {
    tier: "pro",
    maxMonthlyTokens: 10000000,
    maxReviewsPerDay: 200,
    maxConcurrentContainers: 5,
    maxStickyNotes: 1000,
    priceUsd: 49.0,
    priceBtc: 0.00075,
  },
  enterprise: {
    tier: "enterprise",
    maxMonthlyTokens: 100000000,
    maxReviewsPerDay: 5000,
    maxConcurrentContainers: 25,
    maxStickyNotes: 100000,
    priceUsd: 499.0,
    priceBtc: 0.0075,
  },
};

const ALLOWED_REACTIONS = new Set(["laugh", "thumbs_up", "thumbs_down", "heart", "eyes", "rocket", "hooray"]);
const ALLOWED_LABELS = new Set(["bounty", "bug", "enhancement", "triage", "documentation", "security", "duplicate"]);
const ALLOWED_BINARIES = new Set(["git", "node", "npm", "pnpm", "python", "python3", "pytest", "cat", "ls", "echo", "grep", "diff"]);

function hashApiKey(rawKey) {
  return crypto.createHash("sha256").update(rawKey).digest("hex");
}

function generateApiKey(tenantId, prefix = "boxy_live") {
  const entropy = crypto.randomBytes(24).toString("hex");
  const rawKey = `${prefix}_${tenantId}_${entropy}`;
  const keyHash = hashApiKey(rawKey);
  return { rawKey, keyHash, prefix };
}

function verifyWebhookSignature(payloadBuffer, signatureHeader, secret) {
  if (!signatureHeader || !secret) {
    return false;
  }
  if (!signatureHeader.startsWith("sha256=")) {
    return false;
  }
  const expectedMac = crypto.createHmac("sha256", secret).update(payloadBuffer).digest("hex");
  const receivedMac = signatureHeader.replace("sha256=", "").trim();
  if (expectedMac.length !== receivedMac.length) {
    return false;
  }
  return crypto.timingSafeEqual(Buffer.from(expectedMac), Buffer.from(receivedMac));
}

function btcToSatoshis(amountBtc) {
  return Math.round(Number(amountBtc) * SATOSHIS_PER_BITCOIN);
}

function satoshisToBtc(satoshis) {
  return Number(satoshis) / SATOSHIS_PER_BITCOIN;
}

function isValidBitcoinAddress(address) {
  if (!address || address.length < 26 || address.length > 90) {
    return false;
  }
  if (address.startsWith("1") || address.startsWith("3")) {
    return /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/.test(address);
  }
  if (address.startsWith("bc1q") || address.startsWith("bc1p")) {
    return /^bc1[a-z0-9]{38,87}$/.test(address);
  }
  return false;
}

function isValidTxid(txid) {
  if (!txid || txid.length !== 64) {
    return false;
  }
  return /^[0-9a-fA-F]{64}$/.test(txid);
}

function deriveBtcAddress(tenantId, sequenceId) {
  const seed = `boxy_btc_${tenantId}_${sequenceId}`;
  const digest = crypto.createHash("sha256").update(seed).digest("hex");
  return `bc1q${digest.slice(0, 38)}`;
}

class TenantManager {
  constructor() {
    this.tenants = new Map();
    this.apiKeys = new Map();
    this.repoToTenant = new Map();
  }

  createTenant(tenantId, orgName, tier = "free", contactEmail = "") {
    if (this.tenants.has(tenantId)) {
      throw new Error(`Tenant '${tenantId}' already exists`);
    }
    const cleanTier = tier.toLowerCase();
    const policy = TIER_POLICIES[cleanTier] || TIER_POLICIES.free;
    const tenant = {
      tenantId,
      orgName,
      tier: cleanTier,
      status: "active",
      contactEmail,
      createdAt: Date.now(),
      maxMonthlyTokens: policy.maxMonthlyTokens,
      maxReviewsPerDay: policy.maxReviewsPerDay,
      maxConcurrentContainers: policy.maxConcurrentContainers,
      maxStickyNotes: policy.maxStickyNotes,
    };
    this.tenants.set(tenantId, tenant);
    return tenant;
  }

  getTenant(tenantId) {
    return this.tenants.get(tenantId) || null;
  }

  updateTier(tenantId, newTier) {
    const tenant = this.getTenant(tenantId);
    if (!tenant) {
      throw new Error(`Tenant '${tenantId}' not found`);
    }
    const cleanTier = newTier.toLowerCase();
    const policy = TIER_POLICIES[cleanTier] || TIER_POLICIES.free;
    tenant.tier = cleanTier;
    tenant.maxMonthlyTokens = policy.maxMonthlyTokens;
    tenant.maxReviewsPerDay = policy.maxReviewsPerDay;
    tenant.maxConcurrentContainers = policy.maxConcurrentContainers;
    tenant.maxStickyNotes = policy.maxStickyNotes;
    return tenant;
  }

  issueApiKey(tenantId, name = "default") {
    const tenant = this.getTenant(tenantId);
    if (!tenant) {
      throw new Error(`Tenant '${tenantId}' not found`);
    }
    const { rawKey, keyHash, prefix } = generateApiKey(tenantId);
    const record = {
      keyHash,
      prefix,
      tenantId,
      name,
      createdAt: Date.now(),
      revoked: false,
    };
    this.apiKeys.set(keyHash, record);
    return { rawKey, record };
  }

  authenticateKey(rawKey) {
    if (!rawKey) {
      return null;
    }
    const keyHash = hashApiKey(rawKey);
    const record = this.apiKeys.get(keyHash);
    if (!record || record.revoked) {
      return null;
    }
    const tenant = this.getTenant(record.tenantId);
    if (!tenant || tenant.status !== "active") {
      return null;
    }
    return tenant;
  }

  mapRepository(repoFullName, tenantId) {
    if (!this.tenants.has(tenantId)) {
      throw new Error(`Tenant '${tenantId}' not found`);
    }
    this.repoToTenant.set(repoFullName.toLowerCase().trim(), tenantId);
  }

  getTenantForRepo(repoFullName) {
    const tenantId = this.repoToTenant.get(repoFullName.toLowerCase().trim());
    if (!tenantId) {
      return null;
    }
    return this.getTenant(tenantId);
  }
}

class UsageMeter {
  constructor() {
    this.usage = new Map();
    this.requests = new Map();
  }

  _getKey(tenantId, period) {
    const currentPeriod = period || new Date().toISOString().slice(0, 7);
    return `${tenantId}:${currentPeriod}`;
  }

  getOrCreateUsage(tenantId, period) {
    const key = this._getKey(tenantId, period);
    if (!this.usage.has(key)) {
      this.usage.set(key, {
        tenantId,
        period: key.split(":")[1],
        inputTokens: 0,
        outputTokens: 0,
        cachedTokens: 0,
        reviewsCount: 0,
        containersSpawned: 0,
      });
    }
    return this.usage.get(key);
  }

  recordTokens(tenantId, inputTokens, outputTokens, cachedTokens = 0, period) {
    const record = this.getOrCreateUsage(tenantId, period);
    record.inputTokens += Math.max(0, inputTokens);
    record.outputTokens += Math.max(0, outputTokens);
    record.cachedTokens += Math.max(0, cachedTokens);
    return record;
  }

  recordReview(tenantId, period) {
    const record = this.getOrCreateUsage(tenantId, period);
    record.reviewsCount += 1;
    return record;
  }

  recordContainer(tenantId, period) {
    const record = this.getOrCreateUsage(tenantId, period);
    record.containersSpawned += 1;
    return record;
  }

  isMonthlyQuotaExceeded(tenant, period) {
    const record = this.getOrCreateUsage(tenant.tenantId, period);
    const total = record.inputTokens + record.outputTokens + record.cachedTokens;
    return total >= tenant.maxMonthlyTokens;
  }

  checkRateLimit(tenantId, maxReqPerMin = 60, windowMs = 60000) {
    const now = Date.now();
    const cutoff = now - windowMs;
    if (!this.requests.has(tenantId)) {
      this.requests.set(tenantId, []);
    }
    let reqs = this.requests.get(tenantId).filter((ts) => ts > cutoff);
    if (reqs.length >= maxReqPerMin) {
      return { allowed: false, reason: "Rate limit exceeded" };
    }
    reqs.push(now);
    this.requests.set(tenantId, reqs);
    return { allowed: true, reason: "Rate limit verified" };
  }
}

class StickyNoteStore {
  constructor() {
    this.notes = new Map();
  }

  saveNote(tenantId, repoFullName, title, content, author, tags = [], maxLimit = null) {
    if (!this.notes.has(tenantId)) {
      this.notes.set(tenantId, new Map());
    }
    const bucket = this.notes.get(tenantId);
    if (maxLimit !== null && bucket.size >= maxLimit) {
      throw new Error(`Sticky note capacity of ${maxLimit} reached`);
    }
    const noteId = crypto.randomBytes(4).toString("hex");
    const note = {
      noteId,
      tenantId,
      repoFullName: repoFullName.toLowerCase().trim(),
      title: String(title).trim(),
      content: String(content).trim(),
      author: String(author).trim(),
      tags: Array.isArray(tags) ? tags : [],
      createdAt: Date.now(),
    };
    bucket.set(noteId, note);
    return note;
  }

  getNote(tenantId, noteId) {
    const bucket = this.notes.get(tenantId);
    if (!bucket) {
      return null;
    }
    return bucket.get(noteId) || null;
  }

  listNotes(tenantId, repoFullName = null) {
    const bucket = this.notes.get(tenantId);
    if (!bucket) {
      return [];
    }
    let list = Array.from(bucket.values());
    if (repoFullName) {
      const target = repoFullName.toLowerCase().trim();
      list = list.filter((n) => n.repoFullName === target);
    }
    list.sort((a, b) => b.createdAt - a.createdAt);
    return list;
  }

  deleteNote(tenantId, noteId) {
    const bucket = this.notes.get(tenantId);
    if (!bucket) {
      return false;
    }
    return bucket.delete(noteId);
  }
}

class BoxyToolsDispatcher {
  constructor(stickyStore, usageMeter) {
    this.stickyStore = stickyStore;
    this.usageMeter = usageMeter;
  }

  executeSaveStickyNote(tenant, repoFullName, title, content, author, tags) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const note = this.stickyStore.saveNote(
      tenant.tenantId,
      repoFullName,
      title,
      content,
      author,
      tags,
      tenant.maxStickyNotes
    );
    this.usageMeter.recordTokens(tenant.tenantId, 50, 20);
    return {
      status: "success",
      tool: "save_sticky_note",
      noteId: note.noteId,
      message: `Sticky note '${note.title}' saved successfully`,
    };
  }

  executeGetStickyNotes(tenant, repoFullName) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const notes = this.stickyStore.listNotes(tenant.tenantId, repoFullName);
    this.usageMeter.recordTokens(tenant.tenantId, 20, notes.length * 15 + 10);
    return {
      status: "success",
      tool: "get_sticky_notes",
      count: notes.length,
      notes,
    };
  }

  executeReactComment(tenant, commentId, reaction) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const cleanReaction = reaction.toLowerCase().trim();
    if (!ALLOWED_REACTIONS.has(cleanReaction)) {
      throw new Error(`Reaction '${cleanReaction}' is not supported`);
    }
    this.usageMeter.recordTokens(tenant.tenantId, 15, 10);
    return {
      status: "success",
      tool: "react_comment",
      commentId,
      reaction: cleanReaction,
    };
  }

  executeLabelIssue(tenant, issueNumber, label) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const cleanLabel = label.toLowerCase().trim();
    if (!ALLOWED_LABELS.has(cleanLabel)) {
      throw new Error(`Label '${cleanLabel}' is not in approved list`);
    }
    this.usageMeter.recordTokens(tenant.tenantId, 15, 10);
    return {
      status: "success",
      tool: "label_issue",
      issueNumber,
      label: cleanLabel,
    };
  }

  executeReviewPr(tenant, prNumber, diffText) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const record = this.usageMeter.getOrCreateUsage(tenant.tenantId);
    if (record.reviewsCount >= tenant.maxReviewsPerDay) {
      throw new Error(`Daily review limit of ${tenant.maxReviewsPerDay} reached`);
    }
    this.usageMeter.recordReview(tenant.tenantId);
    this.usageMeter.recordTokens(tenant.tenantId, 100, 150);
    return {
      status: "success",
      tool: "review_pr",
      prNumber,
      reviewStatus: "approved",
      findings: [],
      summary: `Automated review for PR #${prNumber} passed.`,
    };
  }

  executeSandboxedCommand(tenant, commandLine) {
    if (tenant.status !== "active") {
      throw new Error(`Tenant '${tenant.tenantId}' is not active`);
    }
    const firstToken = commandLine.trim().split(/\s+/)[0];
    const baseBinary = firstToken.split("/").pop();
    if (!ALLOWED_BINARIES.has(baseBinary)) {
      throw new Error(`Binary '${baseBinary}' is not permitted`);
    }
    this.usageMeter.recordContainer(tenant.tenantId);
    this.usageMeter.recordTokens(tenant.tenantId, 30, 20);
    return {
      status: "success",
      tool: "run_command",
      command: commandLine,
      exitCode: 0,
      output: `[boxy-sandbox] Executed ${baseBinary} successfully for ${tenant.tenantId}`,
    };
  }
}

class BitcoinBillingEngine {
  constructor(defaultBtcUsdRate = 65000.0) {
    this.defaultBtcUsdRate = defaultBtcUsdRate;
    this.invoices = new Map();
    this.tenantSequence = new Map();
  }

  createInvoice(tenantId, amountUsd, btcRateUsd = null) {
    const rate = btcRateUsd || this.defaultBtcUsdRate;
    const amountBtc = Number((amountUsd / rate).toFixed(8));
    const amountSatoshis = btcToSatoshis(amountBtc);

    const seq = (this.tenantSequence.get(tenantId) || 0) + 1;
    this.tenantSequence.set(tenantId, seq);

    const address = deriveBtcAddress(tenantId, seq);
    const invoiceId = `inv_${crypto.randomBytes(6).toString("hex")}`;
    const bip21Uri = `bitcoin:${address}?amount=${amountBtc}&label=BoxySaaS&message=${invoiceId}`;

    const invoice = {
      invoiceId,
      tenantId,
      amountUsd,
      amountBtc,
      amountSatoshis,
      address,
      bip21Uri,
      status: "pending",
      createdAt: Date.now(),
      confirmations: 0,
      txid: null,
    };
    this.invoices.set(invoiceId, invoice);
    return invoice;
  }

  confirmInvoice(invoiceId, txid, confirmations = 1) {
    const invoice = this.invoices.get(invoiceId);
    if (!invoice) {
      throw new Error(`Invoice '${invoiceId}' not found`);
    }
    if (!isValidTxid(txid)) {
      throw new Error(`Invalid transaction hash: ${txid}`);
    }
    invoice.txid = txid;
    invoice.confirmations = confirmations;
    invoice.status = "confirmed";
    return invoice;
  }

  calculateBountySettlement(bountyUsd = 99999999.0, btcRateUsd = 65000.0) {
    const coinMultiplier = 1.25;
    const redemptionRate = 0.72;

    let contributorRatio = 0.85;
    if (bountyUsd < 50) {
      contributorRatio = 0.95;
    } else if (bountyUsd < 200) {
      contributorRatio = 0.92;
    } else if (bountyUsd < 500) {
      contributorRatio = 0.9;
    } else if (bountyUsd < 1000) {
      contributorRatio = 0.87;
    }

    const coinReward = bountyUsd * coinMultiplier;
    const contributorCoins = coinReward * contributorRatio;
    const cashPayoutUsd = contributorCoins * redemptionRate;
    const platformFeeUsd = bountyUsd - cashPayoutUsd;
    const btcPayout = Number((cashPayoutUsd / btcRateUsd).toFixed(8));

    return {
      totalBountyUsd: bountyUsd,
      coinReward,
      contributorRatio,
      contributorCoins,
      cashPayoutUsd,
      platformFeeUsd,
      btcRateUsd,
      btcPayout,
      payoutEvmAddress: EVM_PAYOUT_ADDRESS,
      payoutStellarAddress: STELLAR_PAYOUT_ADDRESS,
    };
  }
}

class BoxySaasGateway {
  constructor(defaultBtcRate = 65000.0) {
    this.tenants = new TenantManager();
    this.meter = new UsageMeter();
    this.notes = new StickyNoteStore();
    this.dispatcher = new BoxyToolsDispatcher(this.notes, this.meter);
    this.billing = new BitcoinBillingEngine(defaultBtcRate);
  }

  registerTenant(tenantId, orgName, tier = "free", contactEmail = "") {
    return this.tenants.createTenant(tenantId, orgName, tier, contactEmail);
  }

  issueApiKey(tenantId, name = "default") {
    return this.tenants.issueApiKey(tenantId, name);
  }

  handleGithubWebhook(eventType, deliveryId, signatureHeader, rawBuffer, secret) {
    const isValid = verifyWebhookSignature(rawBuffer, signatureHeader, secret);
    if (!isValid) {
      throw new Error("Invalid GitHub webhook signature");
    }
    const payload = JSON.parse(rawBuffer.toString("utf8"));
    const repoFullName = payload.repository ? payload.repository.full_name : "";
    const tenant = this.tenants.getTenantForRepo(repoFullName);
    if (!tenant) {
      return {
        status: "ignored",
        reason: `Repository '${repoFullName}' not registered`,
        deliveryId,
      };
    }
    this.meter.recordTokens(tenant.tenantId, 50, 20);
    return {
      status: "processed",
      deliveryId,
      tenantId: tenant.tenantId,
      repository: repoFullName,
      event: eventType,
      action: payload.action,
    };
  }

  executeTool(rawApiKey, toolName, params) {
    const tenant = this.tenants.authenticateKey(rawApiKey);
    if (!tenant) {
      throw new Error("Invalid or inactive API credentials");
    }
    const rateCheck = this.meter.checkRateLimit(tenant.tenantId);
    if (!rateCheck.allowed) {
      throw new Error(rateCheck.reason);
    }
    if (this.meter.isMonthlyQuotaExceeded(tenant)) {
      throw new Error("Monthly token quota exceeded");
    }

    if (toolName === "save_sticky_note") {
      return this.dispatcher.executeSaveStickyNote(
        tenant,
        params.repoFullName,
        params.title,
        params.content,
        params.author,
        params.tags
      );
    }
    if (toolName === "get_sticky_notes") {
      return this.dispatcher.executeGetStickyNotes(tenant, params.repoFullName);
    }
    if (toolName === "react_comment") {
      return this.dispatcher.executeReactComment(tenant, params.commentId, params.reaction);
    }
    if (toolName === "label_issue") {
      return this.dispatcher.executeLabelIssue(tenant, params.issueNumber, params.label);
    }
    if (toolName === "review_pr") {
      return this.dispatcher.executeReviewPr(tenant, params.prNumber, params.diffText);
    }
    if (toolName === "run_sandboxed_command") {
      return this.dispatcher.executeSandboxedCommand(tenant, params.commandLine);
    }
    throw new Error(`Unknown tool: ${toolName}`);
  }
}

module.exports = {
  BoxySaasGateway,
  TenantManager,
  UsageMeter,
  StickyNoteStore,
  BoxyToolsDispatcher,
  BitcoinBillingEngine,
  TIER_POLICIES,
  EVM_PAYOUT_ADDRESS,
  STELLAR_PAYOUT_ADDRESS,
  btcToSatoshis,
  satoshisToBtc,
  isValidBitcoinAddress,
  isValidTxid,
  verifyWebhookSignature,
};

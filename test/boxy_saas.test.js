const assert = require("assert");
const crypto = require("crypto");
const {
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
} = require("../src/boxy_saas");

function runTests() {
  const tm = new TenantManager();
  const freeTenant = tm.createTenant("t_free", "Free Org", "free");
  assert.strictEqual(freeTenant.maxMonthlyTokens, 500000);
  assert.strictEqual(freeTenant.maxReviewsPerDay, 10);
  assert.strictEqual(freeTenant.maxConcurrentContainers, 1);

  const proTenant = tm.createTenant("t_pro", "Pro Org", "pro");
  assert.strictEqual(proTenant.maxMonthlyTokens, 10000000);

  const entTenant = tm.createTenant("t_ent", "Ent Org", "enterprise");
  assert.strictEqual(entTenant.maxMonthlyTokens, 100000000);

  tm.updateTier("t_free", "pro");
  assert.strictEqual(freeTenant.tier, "pro");
  assert.strictEqual(freeTenant.maxMonthlyTokens, 10000000);

  const { rawKey, record } = tm.issueApiKey("t_pro", "ci_key");
  assert(rawKey.startsWith("boxy_live_t_pro_"));
  const authed = tm.authenticateKey(rawKey);
  assert.strictEqual(authed.tenantId, "t_pro");
  assert.strictEqual(tm.authenticateKey("invalid_key"), null);

  tm.mapRepository("OmniBlocks/bountyfarmer", "t_pro");
  const repoTenant = tm.getTenantForRepo("omniblocks/bountyfarmer");
  assert.strictEqual(repoTenant.tenantId, "t_pro");
  assert.strictEqual(tm.getTenantForRepo("unknown/repo"), null);

  const meter = new UsageMeter();
  meter.recordTokens("t_meter", 1000, 500, 200, "2026-09");
  const usage = meter.getOrCreateUsage("t_meter", "2026-09");
  assert.strictEqual(usage.inputTokens, 1000);
  assert.strictEqual(usage.outputTokens, 500);
  assert.strictEqual(usage.cachedTokens, 200);

  const rateCheck1 = meter.checkRateLimit("t_rate", 2);
  assert.strictEqual(rateCheck1.allowed, true);
  const rateCheck2 = meter.checkRateLimit("t_rate", 2);
  assert.strictEqual(rateCheck2.allowed, true);
  const rateCheck3 = meter.checkRateLimit("t_rate", 2);
  assert.strictEqual(rateCheck3.allowed, false);

  const store = new StickyNoteStore();
  store.saveNote("t_a", "repo/one", "Note A", "Content A", "user1");
  store.saveNote("t_b", "repo/two", "Note B", "Content B", "user2");

  const notesA = store.listNotes("t_a");
  const notesB = store.listNotes("t_b");
  assert.strictEqual(notesA.length, 1);
  assert.strictEqual(notesB.length, 1);
  assert.strictEqual(notesA[0].title, "Note A");
  assert.strictEqual(notesB[0].title, "Note B");
  assert.strictEqual(store.getNote("t_a", notesB[0].noteId), null);

  const dispatcher = new BoxyToolsDispatcher(store, meter);
  const toolTenant = tm.createTenant("t_dispatch", "Dispatch Org", "pro");

  const saveRes = dispatcher.executeSaveStickyNote(
    toolTenant,
    "repo/dispatch",
    "Deploy SaaS",
    "Deploy Boxy multi-tenant SaaS architecture",
    "boxy-bot",
    ["saas", "deployment"]
  );
  assert.strictEqual(saveRes.status, "success");

  const notesRes = dispatcher.executeGetStickyNotes(toolTenant, "repo/dispatch");
  assert.strictEqual(notesRes.count, 1);
  assert.strictEqual(notesRes.notes[0].title, "Deploy SaaS");

  const reactRes = dispatcher.executeReactComment(toolTenant, 101, "rocket");
  assert.strictEqual(reactRes.status, "success");
  assert.strictEqual(reactRes.reaction, "rocket");

  const labelRes = dispatcher.executeLabelIssue(toolTenant, 1570, "bounty");
  assert.strictEqual(labelRes.status, "success");
  assert.strictEqual(labelRes.label, "bounty");

  const reviewRes = dispatcher.executeReviewPr(toolTenant, 1570, "+ const x = 1;\n");
  assert.strictEqual(reviewRes.status, "success");
  assert.strictEqual(reviewRes.reviewStatus, "approved");

  const cmdRes = dispatcher.executeSandboxedCommand(toolTenant, "git status");
  assert.strictEqual(cmdRes.status, "success");
  assert.strictEqual(cmdRes.exitCode, 0);

  assert.strictEqual(btcToSatoshis(1.0), 100000000);
  assert.strictEqual(btcToSatoshis(0.00000001), 1);
  assert.strictEqual(satoshisToBtc(100000000), 1.0);
  assert.strictEqual(satoshisToBtc(1), 0.00000001);

  assert.strictEqual(isValidBitcoinAddress("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"), true);
  assert.strictEqual(isValidBitcoinAddress("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"), true);
  assert.strictEqual(isValidBitcoinAddress("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"), true);
  assert.strictEqual(isValidBitcoinAddress("invalid_btc_addr"), false);

  const validTx = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
  assert.strictEqual(isValidTxid(validTx), true);
  assert.strictEqual(isValidTxid("invalid_tx"), false);

  const billing = new BitcoinBillingEngine(65000.0);
  const invoice = billing.createInvoice("t_bill", 49.0);
  assert.strictEqual(invoice.amountUsd, 49.0);
  assert.strictEqual(invoice.status, "pending");
  assert(invoice.bip21Uri.startsWith(`bitcoin:${invoice.address}?amount=`));

  const confirmed = billing.confirmInvoice(invoice.invoiceId, validTx, 3);
  assert.strictEqual(confirmed.status, "confirmed");
  assert.strictEqual(confirmed.txid, validTx);
  assert.strictEqual(confirmed.confirmations, 3);

  const settlement = billing.calculateBountySettlement(99999999.0, 65000.0);
  assert.strictEqual(settlement.totalBountyUsd, 99999999.0);
  assert.strictEqual(settlement.coinReward, 124999998.75);
  assert.strictEqual(settlement.contributorRatio, 0.85);
  assert.strictEqual(settlement.contributorCoins, 106249998.9375);
  assert.strictEqual(settlement.cashPayoutUsd, 76499999.235);
  assert.strictEqual(settlement.platformFeeUsd, 23499999.765);
  assert.strictEqual(settlement.payoutEvmAddress, EVM_PAYOUT_ADDRESS);
  assert.strictEqual(settlement.payoutStellarAddress, STELLAR_PAYOUT_ADDRESS);

  const secret = "test_webhook_secret_99";
  const payloadBuf = Buffer.from(JSON.stringify({ hello: "world" }));
  const mac = crypto.createHmac("sha256", secret).update(payloadBuf).digest("hex");
  assert.strictEqual(verifyWebhookSignature(payloadBuf, `sha256=${mac}`, secret), true);
  assert.strictEqual(verifyWebhookSignature(payloadBuf, "sha256=wrong", secret), false);

  const gateway = new BoxySaasGateway();
  gateway.registerTenant("t_gw", "GW Org", "pro");
  const gwKey = gateway.issueApiKey("t_gw", "test_key");
  const gwToolRes = gateway.executeTool(gwKey.rawKey, "save_sticky_note", {
    repoFullName: "OmniBlocks/bountyfarmer",
    title: "Gateway Note",
    content: "Gateway initialized successfully",
    author: "admin",
    tags: ["gateway"],
  });
  assert.strictEqual(gwToolRes.status, "success");

  process.stdout.write("All Node.js Boxy SaaS tests passed successfully.\n");
}

runTests();

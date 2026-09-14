const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("BatchYieldHarvester & SafeERC20 Integration", function () {
  let owner, alice, bob, strategy, unauthorized;
  let harvester, vulnerableHarvester;
  let standardToken, usdtToken, falseToken, revertingToken;

  const INITIAL_VAULT_BALANCE_STD = ethers.parseEther("10000");
  const INITIAL_VAULT_BALANCE_USDT = 10000n * 1000000n;

  beforeEach(async function () {
    [owner, alice, bob, strategy, unauthorized] = await ethers.getSigners();

    const BatchYieldHarvester = await ethers.getContractFactory("BatchYieldHarvester");
    harvester = await BatchYieldHarvester.deploy();

    const VulnerableYieldHarvester = await ethers.getContractFactory("VulnerableYieldHarvester");
    vulnerableHarvester = await VulnerableYieldHarvester.deploy();

    const StandardERC20 = await ethers.getContractFactory("StandardERC20");
    standardToken = await StandardERC20.deploy("Standard USD", "SUSD", 18);

    const USDTNoReturnERC20 = await ethers.getContractFactory("USDTNoReturnERC20");
    usdtToken = await USDTNoReturnERC20.deploy("Tether USD", "USDT", 6);

    const FalseReturnERC20 = await ethers.getContractFactory("FalseReturnERC20");
    falseToken = await FalseReturnERC20.deploy("False USD", "FUSD", 18);

    const RevertingERC20 = await ethers.getContractFactory("RevertingERC20");
    revertingToken = await RevertingERC20.deploy("Revert USD", "RUSD", 18);

    await standardToken.mint(await harvester.getAddress(), INITIAL_VAULT_BALANCE_STD);
    await usdtToken.mint(await harvester.getAddress(), INITIAL_VAULT_BALANCE_USDT);

    await standardToken.mint(await vulnerableHarvester.getAddress(), INITIAL_VAULT_BALANCE_STD);
    await usdtToken.mint(await vulnerableHarvester.getAddress(), INITIAL_VAULT_BALANCE_USDT);

    await falseToken.mint(await harvester.getAddress(), INITIAL_VAULT_BALANCE_STD);
    await revertingToken.mint(await harvester.getAddress(), INITIAL_VAULT_BALANCE_STD);
  });

  it("should successfully harvest standard ERC-20 token yield", async function () {
    const harvestAmount = ethers.parseEther("500");
    const aliceInitial = await standardToken.balanceOf(alice.address);

    await harvester.harvestYield(await standardToken.getAddress(), alice.address, harvestAmount);

    expect(await standardToken.balanceOf(alice.address)).to.equal(aliceInitial + harvestAmount);
    expect(await standardToken.balanceOf(await harvester.getAddress())).to.equal(INITIAL_VAULT_BALANCE_STD - harvestAmount);
  });

  it("should successfully harvest non-standard USDT token yield with SafeERC20", async function () {
    const harvestAmount = 1000n * 1000000n;
    const bobInitial = await usdtToken.balanceOf(bob.address);

    await harvester.harvestYield(await usdtToken.getAddress(), bob.address, harvestAmount);

    expect(await usdtToken.balanceOf(bob.address)).to.equal(bobInitial + harvestAmount);
    expect(await usdtToken.balanceOf(await harvester.getAddress())).to.equal(INITIAL_VAULT_BALANCE_USDT - harvestAmount);
  });

  it("should successfully execute batch harvest across mixed tokens in a single transaction", async function () {
    const tokens = [await standardToken.getAddress(), await usdtToken.getAddress()];
    const recipients = [alice.address, bob.address];
    const amounts = [ethers.parseEther("250"), 750n * 1000000n];

    await harvester.batchHarvestYield(tokens, recipients, amounts);

    expect(await standardToken.balanceOf(alice.address)).to.equal(amounts[0]);
    expect(await usdtToken.balanceOf(bob.address)).to.equal(amounts[1]);
  });

  it("should revert when vulnerable harvester attempts to transfer USDT token", async function () {
    await expect(
      vulnerableHarvester.harvestYieldDirect(await usdtToken.getAddress(), alice.address, 100n * 1000000n)
    ).to.be.reverted;
  });

  it("should revert when vulnerable harvester attempts batch harvest containing USDT", async function () {
    const tokens = [await standardToken.getAddress(), await usdtToken.getAddress()];
    const recipients = [alice.address, bob.address];
    const amounts = [ethers.parseEther("100"), 100n * 1000000n];

    await expect(
      vulnerableHarvester.batchHarvestYieldDirect(tokens, recipients, amounts)
    ).to.be.reverted;
  });

  it("should revert when token returns false on transfer", async function () {
    await falseToken.setShouldFail(true);
    await expect(
      harvester.harvestYield(await falseToken.getAddress(), alice.address, ethers.parseEther("100"))
    ).to.be.reverted;
  });

  it("should revert when token reverts on transfer", async function () {
    await expect(
      harvester.harvestYield(await revertingToken.getAddress(), alice.address, ethers.parseEther("100"))
    ).to.be.revertedWithCustomError(revertingToken, "TransferBlocked");
  });

  it("should deposit assets via safeTransferFrom for standard and non-standard tokens", async function () {
    const stdDeposit = ethers.parseEther("1000");
    const usdtDeposit = 1000n * 1000000n;

    await standardToken.mint(owner.address, stdDeposit);
    await usdtToken.mint(owner.address, usdtDeposit);

    await standardToken.approve(await harvester.getAddress(), stdDeposit);
    await usdtToken.approve(await harvester.getAddress(), usdtDeposit);

    await harvester.depositAsset(await standardToken.getAddress(), stdDeposit);
    await harvester.depositAsset(await usdtToken.getAddress(), usdtDeposit);

    expect(await standardToken.balanceOf(await harvester.getAddress())).to.equal(INITIAL_VAULT_BALANCE_STD + stdDeposit);
    expect(await usdtToken.balanceOf(await harvester.getAddress())).to.equal(INITIAL_VAULT_BALANCE_USDT + usdtDeposit);
  });

  it("should withdraw assets to destination using safeTransfer", async function () {
    const withdrawAmount = 2000n * 1000000n;
    await harvester.withdrawAsset(await usdtToken.getAddress(), bob.address, withdrawAmount);
    expect(await usdtToken.balanceOf(bob.address)).to.equal(withdrawAmount);
  });

  it("should reinvest yield using forceApprove to handle non-standard allowance updates", async function () {
    const initialAllowance = 1000n * 1000000n;
    const updatedAllowance = 2000n * 1000000n;

    await harvester.reinvestYield(await usdtToken.getAddress(), strategy.address, initialAllowance);
    expect(await usdtToken.allowance(await harvester.getAddress(), strategy.address)).to.equal(initialAllowance);

    await harvester.reinvestYield(await usdtToken.getAddress(), strategy.address, updatedAllowance);
    expect(await usdtToken.allowance(await harvester.getAddress(), strategy.address)).to.equal(updatedAllowance);
  });

  it("should revert batch harvest when array lengths mismatch", async function () {
    const tokens = [await standardToken.getAddress(), await usdtToken.getAddress()];
    const recipients = [alice.address];
    const amounts = [ethers.parseEther("100"), 100n * 1000000n];

    await expect(
      harvester.batchHarvestYield(tokens, recipients, amounts)
    ).to.be.revertedWithCustomError(harvester, "LengthMismatch");
  });

  it("should revert on zero address or zero amount", async function () {
    await expect(
      harvester.harvestYield(ethers.ZeroAddress, alice.address, ethers.parseEther("100"))
    ).to.be.revertedWithCustomError(harvester, "ZeroAddress");

    await expect(
      harvester.harvestYield(await standardToken.getAddress(), ethers.ZeroAddress, ethers.parseEther("100"))
    ).to.be.revertedWithCustomError(harvester, "ZeroAddress");

    await expect(
      harvester.harvestYield(await standardToken.getAddress(), alice.address, 0)
    ).to.be.revertedWithCustomError(harvester, "ZeroAmount");
  });

  it("should revert when called by unauthorized account", async function () {
    await expect(
      harvester.connect(unauthorized).harvestYield(await standardToken.getAddress(), alice.address, ethers.parseEther("100"))
    ).to.be.revertedWithCustomError(harvester, "Unauthorized");
  });

  it("should revert when harvest exceeds available vault balance", async function () {
    const excessiveAmount = ethers.parseEther("20000");
    await expect(
      harvester.harvestYield(await standardToken.getAddress(), alice.address, excessiveAmount)
    ).to.be.revertedWithCustomError(harvester, "InsufficientBalance");
  });
});

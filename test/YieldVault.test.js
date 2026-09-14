const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * Test suite verifying ERC-4626 implementation, virtual share inflation mitigation, and reentrancy protection.
 */
describe("YieldVault", function () {
  let asset;
  let vault;
  let owner;
  let attacker;
  let victim;
  let other;

  const ONE_ETHER = ethers.parseEther("1.0");

  beforeEach(async function () {
    [owner, attacker, victim, other] = await ethers.getSigners();

    const MockERC20Factory = await ethers.getContractFactory("MockERC20");
    asset = await MockERC20Factory.deploy("Underlying Asset", "ASSET", 18);
    await asset.waitForDeployment();

    const YieldVaultFactory = await ethers.getContractFactory("YieldVault");
    vault = await YieldVaultFactory.deploy(await asset.getAddress());
    await vault.waitForDeployment();

    await asset.mint(owner.address, ethers.parseEther("1000"));
    await asset.mint(attacker.address, ethers.parseEther("1000"));
    await asset.mint(victim.address, ethers.parseEther("1000"));
  });

  describe("Initial State & Metadata", function () {
    it("should set correct underlying asset address", async function () {
      expect(await vault.asset()).to.equal(await asset.getAddress());
    });

    it("should configure decimal offset correctly", async function () {
      expect(await vault.decimalsOffset()).to.equal(3);
    });

    it("should reflect asset decimals plus decimals offset", async function () {
      const assetDecimals = await asset.decimals();
      const vaultDecimals = await vault.decimals();
      expect(vaultDecimals).to.equal(assetDecimals + 3n);
    });

    it("should report zero totalAssets initially", async function () {
      expect(await vault.totalAssets()).to.equal(0n);
      expect(await vault.totalSupply()).to.equal(0n);
    });
  });

  describe("Standard Deposit & Withdrawal", function () {
    it("should allow deposits and mint proportional shares", async function () {
      const depositAmount = ethers.parseEther("10");
      await asset.connect(victim).approve(await vault.getAddress(), depositAmount);

      const previewShares = await vault.previewDeposit(depositAmount);
      const tx = await vault.connect(victim).deposit(depositAmount, victim.address);
      await expect(tx).to.emit(vault, "Deposit");

      expect(await vault.balanceOf(victim.address)).to.equal(previewShares);
      expect(await vault.totalAssets()).to.equal(depositAmount);
    });

    it("should allow redeem of shares for underlying assets", async function () {
      const depositAmount = ethers.parseEther("5");
      await asset.connect(victim).approve(await vault.getAddress(), depositAmount);
      await vault.connect(victim).deposit(depositAmount, victim.address);

      const victimShares = await vault.balanceOf(victim.address);
      const balanceBefore = await asset.balanceOf(victim.address);

      await vault.connect(victim).approve(await vault.getAddress(), victimShares);
      await vault.connect(victim).redeem(victimShares, victim.address, victim.address);

      const balanceAfter = await asset.balanceOf(victim.address);
      expect(balanceAfter).to.be.greaterThan(balanceBefore);
      expect(await vault.balanceOf(victim.address)).to.equal(0n);
    });

    it("should allow withdraw specifying asset amount", async function () {
      const depositAmount = ethers.parseEther("10");
      await asset.connect(victim).approve(await vault.getAddress(), depositAmount);
      await vault.connect(victim).deposit(depositAmount, victim.address);

      const withdrawAmount = ethers.parseEther("4");
      await vault.connect(victim).withdraw(withdrawAmount, victim.address, victim.address);

      expect(await vault.totalAssets()).to.equal(depositAmount - withdrawAmount);
    });
  });

  describe("Inflation and Donation Attack Mitigation", function () {
    it("should prevent zero-share rounding loss from donation attack", async function () {
      const vaultAddress = await vault.getAddress();

      await asset.connect(attacker).approve(vaultAddress, 1n);
      await vault.connect(attacker).deposit(1n, attacker.address);

      const attackerInitialShares = await vault.balanceOf(attacker.address);
      expect(attackerInitialShares).to.equal(1000n);

      const donationAmount = ONE_ETHER;
      await asset.connect(attacker).transfer(vaultAddress, donationAmount);

      const victimDeposit = ONE_ETHER;
      await asset.connect(victim).approve(vaultAddress, victimDeposit);

      const expectedShares = await vault.previewDeposit(victimDeposit);
      expect(expectedShares).to.be.greaterThan(0n);

      await vault.connect(victim).deposit(victimDeposit, victim.address);
      const victimShares = await vault.balanceOf(victim.address);
      expect(victimShares).to.equal(expectedShares);
      expect(victimShares).to.be.greaterThan(0n);

      await vault.connect(victim).redeem(victimShares, victim.address, victim.address);
      const victimAssetsRecovered = await asset.balanceOf(victim.address);
      const victimNetLoss = victimDeposit - (victimAssetsRecovered - (ethers.parseEther("1000") - victimDeposit));
      expect(victimNetLoss).to.be.lessThan(ethers.parseEther("0.01"));

      const attackerBalanceBeforeRedeem = await asset.balanceOf(attacker.address);
      await vault.connect(attacker).redeem(attackerInitialShares, attacker.address, attacker.address);
      const attackerBalanceAfterRedeem = await asset.balanceOf(attacker.address);
      const attackerAssetsReturned = attackerBalanceAfterRedeem - attackerBalanceBeforeRedeem;

      expect(attackerAssetsReturned).to.be.lessThan(ethers.parseEther("0.55"));
      expect(donationAmount - attackerAssetsReturned).to.be.greaterThan(ethers.parseEther("0.45"));
    });

    it("should mint non-zero shares for small deposits after donation", async function () {
      const vaultAddress = await vault.getAddress();

      await asset.connect(attacker).approve(vaultAddress, 1n);
      await vault.connect(attacker).deposit(1n, attacker.address);

      await asset.connect(attacker).transfer(vaultAddress, ethers.parseEther("1"));

      const smallDeposit = ethers.parseEther("0.01");
      await asset.connect(victim).approve(vaultAddress, smallDeposit);

      const victimPreview = await vault.previewDeposit(smallDeposit);
      expect(victimPreview).to.be.greaterThan(0n);

      await vault.connect(victim).deposit(smallDeposit, victim.address);
      expect(await vault.balanceOf(victim.address)).to.equal(victimPreview);
    });
  });

  describe("Reentrancy Protection", function () {
    let reentrantAsset;
    let protectedVault;

    beforeEach(async function () {
      const ReentrantFactory = await ethers.getContractFactory("ReentrantERC20");
      reentrantAsset = await ReentrantFactory.deploy();
      await reentrantAsset.waitForDeployment();

      const VaultFactory = await ethers.getContractFactory("YieldVault");
      protectedVault = await VaultFactory.deploy(await reentrantAsset.getAddress());
      await protectedVault.waitForDeployment();

      await reentrantAsset.setTargetVault(await protectedVault.getAddress());
      await reentrantAsset.mint(victim.address, ethers.parseEther("100"));
    });

    it("should revert when an asset triggers reentrancy during deposit", async function () {
      const depositAmount = ethers.parseEther("10");
      await reentrantAsset.connect(victim).approve(await protectedVault.getAddress(), ethers.parseEther("50"));
      await reentrantAsset.setAttackOnTransferFrom(true);

      await expect(
        protectedVault.connect(victim).deposit(depositAmount, victim.address)
      ).to.be.revertedWithCustomError(protectedVault, "ReentrancyGuardReentrantCall");
    });
  });
});

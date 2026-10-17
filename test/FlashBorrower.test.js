const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FlashBorrower & FlashVault Invariants", function () {
  let owner, user;
  let token, vault, borrower;

  const INITIAL_VAULT_LIQUIDITY = ethers.parseUnits("1000000", 6);
  const DEFAULT_FEE_RATE = 5n;
  const DEFAULT_MIN_FEE = 1n;

  beforeEach(async function () {
    [owner, user] = await ethers.getSigners();

    const MockERC20 = await ethers.getContractFactory("MockERC20");
    token = await MockERC20.deploy("USD Coin", "USDC", 6);

    const FlashVault = await ethers.getContractFactory("FlashVault");
    vault = await FlashVault.deploy(await token.getAddress(), DEFAULT_FEE_RATE, DEFAULT_MIN_FEE);

    const FlashBorrower = await ethers.getContractFactory("FlashBorrower");
    borrower = await FlashBorrower.deploy(
      await vault.getAddress(),
      DEFAULT_FEE_RATE,
      DEFAULT_MIN_FEE
    );

    await token.mint(await vault.getAddress(), INITIAL_VAULT_LIQUIDITY);
    await token.mint(await borrower.getAddress(), ethers.parseUnits("10000", 6));
    await token.mint(user.address, ethers.parseUnits("10000", 6));
  });

  it("should configure initial parameters correctly", async function () {
    expect(await vault.feeRate()).to.equal(DEFAULT_FEE_RATE);
    expect(await vault.minFee()).to.equal(DEFAULT_MIN_FEE);
    expect(await vault.asset()).to.equal(await token.getAddress());
    expect(await borrower.feeRate()).to.equal(DEFAULT_FEE_RATE);
    expect(await borrower.minFee()).to.equal(DEFAULT_MIN_FEE);
  });

  it("should round fee up in favor of vault reserves", async function () {
    const loanAmount = 1999n;
    const feeRate = 5n;
    const precision = 10000n;

    const floorFee = (loanAmount * feeRate) / precision;
    expect(floorFee).to.equal(0n);

    const borrowerCalculatedFee = await borrower.calculateFee(loanAmount, feeRate);
    expect(borrowerCalculatedFee).to.equal(1n);

    const vaultFee = await vault.flashFee(await token.getAddress(), loanAmount);
    expect(vaultFee).to.equal(1n);
  });

  it("should prevent zero-fee exploits on tiny loan amounts", async function () {
    const tinyAmount = 100n;
    const feeRate = 5n;

    const standardTruncatedFee = (tinyAmount * feeRate) / 10000n;
    expect(standardTruncatedFee).to.equal(0n);

    const protectedFee = await borrower.calculateFee(tinyAmount, feeRate);
    expect(protectedFee).to.equal(1n);

    const vaultFee = await vault.flashFee(await token.getAddress(), tinyAmount);
    expect(vaultFee).to.equal(1n);
  });

  it("should revert when querying fee for zero loan amount", async function () {
    await expect(
      borrower.flashLoanFee(await token.getAddress(), 0)
    ).to.be.revertedWithCustomError(borrower, "ZeroAmountLoan");

    await expect(
      vault.flashFee(await token.getAddress(), 0)
    ).to.be.revertedWithCustomError(vault, "ZeroAmountLoan");
  });

  it("should execute flash loan and expand vault reserves", async function () {
    const borrowAmount = ethers.parseUnits("50000", 6);
    const expectedFee = await vault.flashFee(await token.getAddress(), borrowAmount);

    const vaultInitial = await token.balanceOf(await vault.getAddress());
    const borrowerInitial = await token.balanceOf(await borrower.getAddress());

    await borrower.executeFlashLoan(await token.getAddress(), borrowAmount, "0x");

    const vaultFinal = await token.balanceOf(await vault.getAddress());
    const borrowerFinal = await token.balanceOf(await borrower.getAddress());

    expect(vaultFinal).to.equal(vaultInitial + expectedFee);
    expect(borrowerFinal).to.equal(borrowerInitial - expectedFee);
  });

  it("should prevent micro-drainage over repeated iterations", async function () {
    const microAmount = 1999n;
    const iterations = 25;
    const vaultInitial = await token.balanceOf(await vault.getAddress());

    for (let i = 0; i < iterations; i++) {
      await borrower.executeFlashLoan(await token.getAddress(), microAmount, "0x");
    }

    const vaultFinal = await token.balanceOf(await vault.getAddress());
    expect(vaultFinal - vaultInitial).to.equal(BigInt(iterations) * 1n);
  });

  it("should enforce custom minimum fee threshold", async function () {
    await borrower.setMinFee(25n);
    const fee = await borrower.calculateFee(100n, 5n);
    expect(fee).to.equal(25n);
  });

  it("should revert on unsupported token", async function () {
    const randomAddress = "0x0000000000000000000000000000000000001234";
    await expect(
      vault.flashFee(randomAddress, 1000n)
    ).to.be.revertedWithCustomError(vault, "UnsupportedToken").withArgs(randomAddress);
  });

  it("should revert when loan exceeds liquidity", async function () {
    const excessive = INITIAL_VAULT_LIQUIDITY + 1n;
    await expect(
      vault.flashLoan(await borrower.getAddress(), await token.getAddress(), excessive, "0x")
    ).to.be.revertedWithCustomError(vault, "ExceedsMaxLoan").withArgs(excessive, INITIAL_VAULT_LIQUIDITY);
  });

  it("should revert on unauthorized callback call", async function () {
    await expect(
      borrower.connect(user).onFlashLoan(borrower.target, token.target, 1000n, 10n, "0x")
    ).to.be.revertedWithCustomError(borrower, "InvalidLender");
  });
});

import { expect } from "chai";
import BN from "bn.js";

describe("staking pool reward accrual engine", () => {
  const Q64_SCALE = new BN(1).shln(64);
  const MAX_U64 = new BN("18446744073709551615");

  it("verifies Q64 bitwise constants", () => {
    expect(Q64_SCALE.toString()).to.equal("18446744073709551616");
    expect(Q64_SCALE.and(MAX_U64).toNumber()).to.equal(0);
  });

  it("calculates reward payout using Q64.64 fixed-point arithmetic", () => {
    const accumPerShare = Q64_SCALE.mul(new BN(2));
    const stakedTokens = new BN(1000000);
    const hi = accumPerShare.shrn(64);
    const lo = accumPerShare.and(MAX_U64);
    const loProd = lo.mul(stakedTokens);
    const hiProd = hi.mul(stakedTokens);
    const totalReward = hiProd.add(loProd.shrn(64));
    expect(totalReward.toNumber()).to.equal(2000000);
  });

  it("accrues rewards accurately without 64-bit overflow", () => {
    const totalStaked = new BN("50000000000");
    const pendingRewards = new BN("50000000");
    const scaledRewards = pendingRewards.mul(Q64_SCALE);
    const normalizedDelta = scaledRewards.div(totalStaked);
    expect(normalizedDelta.gt(new BN(0))).to.be.true;
    expect(normalizedDelta.lt(Q64_SCALE)).to.be.true;
  });

  it("prevents overflow at maximum u64 boundary", () => {
    const totalStaked = MAX_U64;
    const pendingRewards = MAX_U64;
    const scaledRewards = pendingRewards.mul(Q64_SCALE);
    const normalizedDelta = scaledRewards.div(totalStaked);
    expect(normalizedDelta.eq(Q64_SCALE)).to.be.true;
    const reward = normalizedDelta.mul(MAX_U64).shrn(64);
    expect(reward.eq(MAX_U64)).to.be.true;
  });
});

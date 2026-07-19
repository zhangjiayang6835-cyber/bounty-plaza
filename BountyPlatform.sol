// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyPlatform is Ownable {
    IERC20 public usdc;
    uint256 public constant BOUNTY_AMOUNT = 1 * 10**6; // 1 USDC
    uint256 public constant SOLVER_REWARD = 9 * 10**5; // 0.90 USDC
    uint256 public constant VERIFIER_REWARD = 1 * 10**5; // 0.10 USDC
    uint256 public constant CLAIM_BOND = 1 * 10**5; // 0.10 USDC

    event FundingAdded(uint256 amount);
    event BountyBecameClaimable();
    event BountyClaimed(address indexed solver, address indexed verifier);

    struct Bounty {
        bool active;
        bool funded;
        bool claimable;
        address solver;
        address verifier;
    }

    Bounty public childBounty;

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createBounty() external onlyOwner {
        require(!childBounty.active, "Bounty already created");
        childBounty.active = true;
    }

    function fundBounty() external onlyOwner {
        require(childBounty.active, "Bounty not created yet");
        require(!childBounty.funded, "Bounty already funded");

        uint256 totalAmount = BOUNTY_AMOUNT + CLAIM_BOND;
        require(usdc.transferFrom(msg.sender, address(this), totalAmount), "Transfer failed");

        childBounty.funded = true;
        emit FundingAdded(totalAmount);
    }

    function activateBounty() external onlyOwner {
        require(childBounty.active, "Bounty not created yet");
        require(childBounty.funded, "Bounty not funded yet");
        require(!childBounty.claimable, "Bounty already claimable");

        childBounty.claimable = true;
        emit BountyBecameClaimable();
    }

    function claimBounty(address _solver, address _verifier) external {
        require(childBounty.claimable, "Bounty not claimable yet");
        require(childBounty.solver == address(0), "Bounty already claimed");

        childBounty.solver = _solver;
        childBounty.verifier = _verifier;

        require(usdc.transfer(_solver, SOLVER_REWARD), "Solver reward transfer failed");
        require(usdc.transfer(_verifier, VERIFIER_REWARD), "Verifier reward transfer failed");
        require(usdc.transfer(_solver, CLAIM_BOND), "Claim bond return failed");

        emit BountyClaimed(_solver, _verifier);
    }
}
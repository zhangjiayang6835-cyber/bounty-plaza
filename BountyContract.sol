// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyContract is Ownable {
    IERC20 public usdcToken;
    uint256 public constant BOUNTY_AMOUNT = 1 * 10**6; // 1 USDC
    uint256 public constant SOLVER_REWARD = 900 * 10**3; // 0.90 USDC
    uint256 public constant VERIFIER_REWARD = 100 * 10**3; // 0.10 USDC
    uint256 public constant CLAIM_BOND = 100 * 10**3; // 0.10 USDC

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

    Bounty public bounty;

    constructor(address _usdcToken) {
        usdcToken = IERC20(_usdcToken);
    }

    function addFunding() external onlyOwner {
        require(!bounty.funded, "Bounty already funded");
        require(usdcToken.transferFrom(msg.sender, address(this), BOUNTY_AMOUNT), "Transfer failed");

        bounty.funded = true;
        emit FundingAdded(BOUNTY_AMOUNT);

        if (bounty.active && bounty.funded) {
            bounty.claimable = true;
            emit BountyBecameClaimable();
        }
    }

    function activateBounty() external onlyOwner {
        require(!bounty.active, "Bounty already active");
        bounty.active = true;

        if (bounty.active && bounty.funded) {
            bounty.claimable = true;
            emit BountyBecameClaimable();
        }
    }

    function claimBounty() external {
        require(bounty.claimable, "Bounty not claimable");
        require(bounty.solver == address(0), "Bounty already claimed");

        // Transfer the claim bond from the solver
        require(usdcToken.transferFrom(msg.sender, address(this), CLAIM_BOND), "Transfer failed");

        // Set the solver and verifier
        bounty.solver = msg.sender;
        bounty.verifier = owner();

        // Transfer the rewards
        require(usdcToken.transfer(bounty.solver, SOLVER_REWARD), "Transfer failed");
        require(usdcToken.transfer(bounty.verifier, VERIFIER_REWARD), "Transfer failed");

        // Return the claim bond to the solver
        require(usdcToken.transfer(bounty.solver, CLAIM_BOND), "Transfer failed");

        emit BountyClaimed(bounty.solver, bounty.verifier);
    }

    function getBountyStatus() external view returns (bool, bool, bool) {
        return (bounty.active, bounty.funded, bounty.claimable);
    }
}
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Bounty is Ownable {
    IERC20 public usdc;
    uint256 public solverReward = 0.90 * 1e6; // 0.90 USDC
    uint256 public verifierReward = 0.10 * 1e6; // 0.10 USDC
    uint256 public claimBond = 0.10 * 1e6; // 0.10 USDC

    enum BountyStatus { Created, Funded, Claimable, Claimed }
    BountyStatus public status;

    event FundingAdded(uint256 amount);
    event BountyBecameClaimable();
    event BountyClaimed(address indexed claimer);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
        status = BountyStatus.Created;
    }

    function fundBounty() external onlyOwner {
        require(status == BountyStatus.Created, "Bounty already funded or claimable");
        uint256 totalFunding = solverReward + verifierReward;
        require(usdc.transferFrom(msg.sender, address(this), totalFunding), "Transfer failed");

        emit FundingAdded(totalFunding);
        status = BountyStatus.Funded;
    }

    function activateBounty() external onlyOwner {
        require(status == BountyStatus.Funded, "Bounty not yet funded");
        status = BountyStatus.Claimable;
        emit BountyBecameClaimable();
    }

    function claimBounty() external {
        require(status == BountyStatus.Claimable, "Bounty not claimable");
        require(usdc.transferFrom(msg.sender, address(this), claimBond), "Claim bond transfer failed");

        // Perform verification (this is a placeholder, actual verification logic should be implemented)
        bool verified = true; // Placeholder for actual verification
        if (verified) {
            require(usdc.transfer(msg.sender, solverReward), "Solver reward transfer failed");
            status = BountyStatus.Claimed;
            emit BountyClaimed(msg.sender);
        } else {
            // Return the claim bond if verification fails
            require(usdc.transfer(msg.sender, claimBond), "Claim bond return failed");
        }
    }

    function getBountyStatus() external view returns (BountyStatus) {
        return status;
    }
}
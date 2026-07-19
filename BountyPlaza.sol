// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyPlaza is Ownable {
    IERC20 public usdcToken;
    uint256 public constant USDC_DECIMALS = 1e6; // Assuming 6 decimals for USDC

    struct Bounty {
        address creator;
        uint256 reward;
        bool claimable;
        bool settled;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountySettled(uint256 indexed bountyId, address solver, uint256 reward);

    constructor(address _usdcToken) {
        usdcToken = IERC20(_usdcToken);
    }

    function createBounty(uint256 _reward) external onlyOwner {
        require(_reward > 0, "Reward must be greater than 0");
        bounties[nextBountyId] = Bounty({
            creator: msg.sender,
            reward: _reward * USDC_DECIMALS,
            claimable: false,
            settled: false
        });
        nextBountyId++;
    }

    function addFunding(uint256 _bountyId, uint256 _amount) external onlyOwner {
        require(bounties[_bountyId].creator!= address(0), "Bounty does not exist");
        require(usdcToken.transferFrom(msg.sender, address(this), _amount * USDC_DECIMALS), "Transfer failed");
        bounties[_bountyId].reward += _amount * USDC_DECIMALS;
        emit FundingAdded(_bountyId, _amount * USDC_DECIMALS);
    }

    function makeBountyClaimable(uint256 _bountyId) external onlyOwner {
        require(bounties[_bountyId].creator!= address(0), "Bounty does not exist");
        require(!bounties[_bountyId].claimable, "Bounty is already claimable");
        bounties[_bountyId].claimable = true;
        emit BountyBecameClaimable(_bountyId);
    }

    function settleBounty(uint256 _bountyId, address _solver) external onlyOwner {
        Bounty storage bounty = bounties[_bountyId];
        require(bounty.creator!= address(0), "Bounty does not exist");
        require(bounty.claimable, "Bounty is not claimable");
        require(!bounty.settled, "Bounty is already settled");

        require(usdcToken.transfer(_solver, bounty.reward), "Transfer failed");

        bounty.settled = true;
        emit BountySettled(_bountyId, _solver, bounty.reward);
    }
}
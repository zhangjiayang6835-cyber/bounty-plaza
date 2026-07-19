// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyContract is Ownable {
    IERC20 public usdcToken;
    uint256 public solverReward = 0.90 * 10**6; // 0.90 USDC (assuming 6 decimals)
    uint256 public verifierReward = 0.10 * 10**6; // 0.10 USDC (assuming 6 decimals)
    uint256 public claimBond = 0.10 * 10**6; // 0.10 USDC (assuming 6 decimals)

    enum BountyStatus { Created, Funded, Claimable, Settled }
    struct Bounty {
        address creator;
        BountyStatus status;
        uint256 amount;
        bool claimed;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountySettled(uint256 indexed bountyId, address indexed solver, address indexed verifier);

    constructor(address _usdcToken) {
        usdcToken = IERC20(_usdcToken);
    }

    function createBounty() external onlyOwner {
        require(bounties[nextBountyId].status == BountyStatus.Created, "Bounty already created");
        bounties[nextBountyId] = Bounty({
            creator: msg.sender,
            status: BountyStatus.Created,
            amount: 0,
            claimed: false
        });
        nextBountyId++;
    }

    function fundBounty(uint256 bountyId, uint256 amount) external {
        require(bounties[bountyId].status == BountyStatus.Created, "Bounty not in Created state");
        require(amount >= solverReward, "Funding amount must be at least the solver reward");

        usdcToken.transferFrom(msg.sender, address(this), amount);
        bounties[bountyId].amount += amount;
        bounties[bountyId].status = BountyStatus.Funded;

        emit FundingAdded(bountyId, amount);

        if (bounties[bountyId].amount >= solverReward) {
            bounties[bountyId].status = BountyStatus.Claimable;
            emit BountyBecameClaimable(bountyId);
        }
    }

    function claimBounty(uint256 bountyId) external {
        require(bounties[bountyId].status == BountyStatus.Claimable, "Bounty not in Claimable state");
        require(!bounties[bountyId].claimed, "Bounty already claimed");

        bounties[bountyId].claimed = true;
        bounties[bountyId].status = BountyStatus.Settled;

        usdcToken.transfer(msg.sender, solverReward);
        usdcToken.transfer(owner(), verifierReward);

        emit BountySettled(bountyId, msg.sender, owner());
    }

    function refundClaimBond(uint256 bountyId) external {
        require(bounties[bountyId].status == BountyStatus.Settled, "Bounty not in Settled state");
        require(usdcToken.balanceOf(address(this)) >= claimBond, "Insufficient funds for refund");

        usdcToken.transfer(msg.sender, claimBond);
    }
}
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

contract BountyPlatform is Ownable {
    using SafeMath for uint256;

    IERC20 public usdc;
    uint256 public constant CLAIM_BOND = 100 * 10**6; // 0.10 USDC

    struct Bounty {
        address creator;
        address solver;
        uint256 reward;
        bool claimable;
        bool claimed;
        uint256 verificationDeadline;
    }

    mapping(uint256 => Bounty) public bounties;
    mapping(uint256 => Bounty) public childBounties;
    uint256 public nextBountyId;
    uint256 public nextChildBountyId;

    event BountyCreated(uint256 indexed bountyId, address indexed creator, uint256 reward);
    event ChildBountyCreated(uint256 indexed parentBountyId, uint256 indexed childBountyId, address indexed creator, uint256 reward);
    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountySettled(uint256 indexed bountyId, address indexed solver, uint256 reward);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createBounty(uint256 _reward) external {
        require(usdc.transferFrom(msg.sender, address(this), _reward), "Transfer failed");
        bounties[nextBountyId] = Bounty({
            creator: msg.sender,
            solver: address(0),
            reward: _reward,
            claimable: false,
            claimed: false,
            verificationDeadline: block.timestamp + 7 days
        });
        emit BountyCreated(nextBountyId, msg.sender, _reward);
        nextBountyId++;
    }

    function createChildBounty(uint256 _parentBountyId, uint256 _reward) external {
        require(bounties[_parentBountyId].solver == msg.sender, "Only parent solver can create a child bounty");
        require(usdc.transferFrom(msg.sender, address(this), _reward), "Transfer failed");
        childBounties[nextChildBountyId] = Bounty({
            creator: msg.sender,
            solver: address(0),
            reward: _reward,
            claimable: false,
            claimed: false,
            verificationDeadline: block.timestamp + 7 days
        });
        emit ChildBountyCreated(_parentBountyId, nextChildBountyId, msg.sender, _reward);
        nextChildBountyId++;
    }

    function addFunding(uint256 _bountyId, uint256 _amount) external {
        require(usdc.transferFrom(msg.sender, address(this), _amount), "Transfer failed");
        bounties[_bountyId].reward = bounties[_bountyId].reward.add(_amount);
        emit FundingAdded(_bountyId, _amount);
    }

    function makeBountyClaimable(uint256 _bountyId) external onlyOwner {
        bounties[_bountyId].claimable = true;
        emit BountyBecameClaimable(_bountyId);
    }

    function verifyAndSettle(uint256 _parentBountyId, uint256 _childBountyId, bytes memory _proof) external {
        Bounty storage parentBounty = bounties[_parentBountyId];
        Bounty storage childBounty = childBounties[_childBountyId];

        require(parentBounty.claimable, "Parent bounty not claimable");
        require(childBounty.creator == parentBounty.solver, "Child bounty creator must be parent bounty solver");
        require(block.timestamp <= childBounty.verificationDeadline, "Verification deadline passed");

        (bool success, ) = address(this).call(_proof);
        require(success, "Verification failed");

        if (msg.sender!= childBounty.creator) {
            require(usdc.transferFrom(msg.sender, address(this), CLAIM_BOND), "Claim bond transfer failed");
        }

        parentBounty.solver = msg.sender;
        parentBounty.claimed = true;
        childBounty.claimed = true;

        usdc.transfer(parentBounty.solver, parentBounty.reward);
        usdc.transfer(childBounty.creator, childBounty.reward);

        if (msg.sender!= childBounty.creator) {
            usdc.transfer(msg.sender, CLAIM_BOND); // Return claim bond if verification succeeds
        }

        emit BountySettled(_parentBountyId, parentBounty.solver, parentBounty.reward);
    }

    function handleVerificationTimeout(uint256 _childBountyId) external {
        Bounty storage childBounty = childBounties[_childBountyId];
        require(block.timestamp > childBounty.verificationDeadline, "Verification deadline not passed");

        if (childBounty.creator!= msg.sender) {
            usdc.transfer(msg.sender, CLAIM_BOND); // Return claim bond on timeout
        }
    }
}
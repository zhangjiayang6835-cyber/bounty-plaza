// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyPlatform is Ownable {
    IERC20 public usdcToken;
    uint256 public constant USDC_DECIMALS = 6;

    struct Bounty {
        address creator;
        uint256 amount;
        bool isFunded;
        bool isClaimable;
        bool isClaimed;
        bool isSettled;
        address solver;
        address verifier;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    event BountyCreated(uint256 indexed bountyId, address indexed creator, uint256 amount);
    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountyClaimed(uint256 indexed bountyId, address indexed solver);
    event BountySettled(uint256 indexed bountyId);

    constructor(address _usdcToken) {
        usdcToken = IERC20(_usdcToken);
    }

    function createBounty(uint256 _amount) external onlyOwner {
        require(_amount > 0, "Amount must be greater than 0");
        bounties[nextBountyId] = Bounty({
            creator: msg.sender,
            amount: _amount * (10 ** USDC_DECIMALS),
            isFunded: false,
            isClaimable: false,
            isClaimed: false,
            isSettled: false,
            solver: address(0),
            verifier: address(0)
        });
        emit BountyCreated(nextBountyId, msg.sender, _amount);
        nextBountyId++;
    }

    function fundBounty(uint256 _bountyId) external onlyOwner {
        Bounty storage bounty = bounties[_bountyId];
        require(!bounty.isFunded, "Bounty is already funded");
        require(usdcToken.transferFrom(msg.sender, address(this), bounty.amount), "Transfer failed");
        bounty.isFunded = true;
        emit FundingAdded(_bountyId, bounty.amount);
    }

    function makeBountyClaimable(uint256 _bountyId) external onlyOwner {
        Bounty storage bounty = bounties[_bountyId];
        require(bounty.isFunded, "Bounty is not funded");
        require(!bounty.isClaimable, "Bounty is already claimable");
        bounty.isClaimable = true;
        emit BountyBecameClaimable(_bountyId);
    }

    function claimBounty(uint256 _bountyId) external {
        Bounty storage bounty = bounties[_bountyId];
        require(bounty.isClaimable, "Bounty is not claimable");
        require(bounty.solver == address(0), "Bounty is already claimed");
        bounty.solver = msg.sender;
        bounty.isClaimed = true;
        emit BountyClaimed(_bountyId, msg.sender);
    }

    function settleBounty(uint256 _bountyId) external onlyOwner {
        Bounty storage bounty = bounties[_bountyId];
        require(bounty.isClaimed, "Bounty is not claimed");
        require(!bounty.isSettled, "Bounty is already settled");
        require(usdcToken.transfer(bounty.solver, bounty.amount * 9 / 10), "Transfer to solver failed");
        require(usdcToken.transfer(owner(), bounty.amount * 1 / 10), "Transfer to owner failed");
        bounty.isSettled = true;
        emit BountySettled(_bountyId);
    }
}
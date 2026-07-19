// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountySystem is Ownable {
    // Struct to store bounty details
    struct Bounty {
        address creator;
        uint256 amount;
        bool funded;
        bool claimable;
        bool settled;
        address solver;
        address claimer;
        address verifier;
    }

    // Mapping from bounty ID to Bounty
    mapping(uint256 => Bounty) public bounties;

    // Events
    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountySettled(uint256 indexed bountyId, address indexed solver, address indexed claimer);

    // ERC20 token contract
    IERC20 public usdcToken;

    // Constructor
    constructor(address _usdcToken) {
        usdcToken = IERC20(_usdcToken);
    }

    // Function to create a new bounty
    function createBounty(uint256 _amount) external onlyOwner {
        require(_amount > 0, "Amount must be greater than 0");
        uint256 bountyId = bounties.length;
        bounties[bountyId] = Bounty({
            creator: msg.sender,
            amount: _amount,
            funded: false,
            claimable: false,
            settled: false,
            solver: address(0),
            claimer: address(0),
            verifier: address(0)
        });
    }

    // Function to add funding to a bounty
    function addFunding(uint256 _bountyId) external {
        require(bounties[_bountyId].creator!= address(0), "Bounty does not exist");
        require(!bounties[_bountyId].funded, "Bounty is already funded");
        require(usdcToken.transferFrom(msg.sender, address(this), bounties[_bountyId].amount), "Transfer failed");

        bounties[_bountyId].funded = true;
        emit FundingAdded(_bountyId, bounties[_bountyId].amount);
    }

    // Function to make a bounty claimable
    function makeClaimable(uint256 _bountyId) external onlyOwner {
        require(bounties[_bountyId].funded, "Bounty is not funded");
        bounties[_bountyId].claimable = true;
        emit BountyBecameClaimable(_bountyId);
    }

    // Function to claim a bounty
    function claimBounty(uint256 _bountyId) external {
        require(bounties[_bountyId].claimable, "Bounty is not claimable");
        require(bounties[_bountyId].claimer == address(0), "Bounty is already claimed");
        require(msg.sender!= bounties[_bountyId].creator, "Creator cannot claim the bounty");

        bounties[_bountyId].claimer = msg.sender;
    }

    // Function to settle a bounty
    function settleBounty(uint256 _bountyId, address _solver, address _verifier) external onlyOwner {
        require(bounties[_bountyId].claimer!= address(0), "Bounty is not claimed");
        require(bounties[_bountyId].settled == false, "Bounty is already settled");
        require(_solver!= bounties[_bountyId].claimer, "Solver and claimer must be different");

        bounties[_bountyId].solver = _solver;
        bounties[_bountyId].verifier = _verifier;
        bounties[_bountyId].settled = true;

        // Transfer funds to the solver and verifier
        require(usdcToken.transfer(_solver, (bounties[_bountyId].amount * 90) / 100), "Transfer to solver failed");
        require(usdcToken.transfer(_verifier, (bounties[_bountyId].amount * 10) / 100), "Transfer to verifier failed");

        emit BountySettled(_bountyId, _solver, bounties[_bountyId].claimer);
    }
}
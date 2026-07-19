// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyPlatform is Ownable {
    IERC20 public usdc;
    uint256 public constant SOLVER_REWARD = 90 * 10**6; // 0.90 USDC
    uint256 public constant VERIFIER_REWARD = 10 * 10**6; // 0.10 USDC
    uint256 public constant CLAIM_BOND = 10 * 10**6; // 0.10 USDC

    struct Bounty {
        address solver;
        uint256 reward;
        bool claimable;
        bool claimed;
        uint256 verificationDeadline;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    event FundingAdded(uint256 indexed bountyId, uint256 amount);
    event BountyBecameClaimable(uint256 indexed bountyId);
    event BountySettled(uint256 indexed bountyId, address indexed solver, address indexed claimer);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createBounty() external onlyOwner {
        require(nextBountyId == 0, "Only one bounty can be created");
        bounties[nextBountyId] = Bounty({
            solver: msg.sender,
            reward: 0,
            claimable: false,
            claimed: false,
            verificationDeadline: block.timestamp + 7 days
        });
        nextBountyId++;
    }

    function addFunding(uint256 bountyId, uint256 amount) external {
        require(bountyId < nextBountyId, "Invalid bounty ID");
        require(!bounties[bountyId].claimable, "Bounty is already claimable");
        require(usdc.transferFrom(msg.sender, address(this), amount), "Transfer failed");

        bounties[bountyId].reward += amount;
        emit FundingAdded(bountyId, amount);

        if (bounties[bountyId].reward >= SOLVER_REWARD) {
            bounties[bountyId].claimable = true;
            emit BountyBecameClaimable(bountyId);
        }
    }

    function claimBounty(uint256 bountyId) external {
        require(bountyId < nextBountyId, "Invalid bounty ID");
        Bounty storage bounty = bounties[bountyId];
        require(bounty.claimable, "Bounty is not claimable");
        require(!bounty.claimed, "Bounty has already been claimed");
        require(msg.sender!= bounty.solver, "Solver cannot claim the bounty");
        require(block.timestamp < bounty.verificationDeadline, "Verification deadline passed");

        require(usdc.transfer(bounty.solver, bounty.reward - CLAIM_BOND), "Transfer to solver failed");
        require(usdc.transfer(owner(), CLAIM_BOND), "Transfer to owner failed");

        bounty.claimed = true;
        emit BountySettled(bountyId, bounty.solver, msg.sender);
    }

    function verifyAndSettle(uint256 bountyId, bytes memory proof) external onlyOwner {
        require(bountyId < nextBountyId, "Invalid bounty ID");
        Bounty storage bounty = bounties[bountyId];
        require(bounty.claimed, "Bounty has not been claimed");

        (address childBounty) = abi.decode(proof, (address));
        require(childBounty!= address(0), "Invalid proof");

        // Additional verification logic can be added here
        // For example, checking the childBounty's creator, funding, and other conditions

        // Assuming the verification is successful
        require(usdc.transfer(bounty.solver, VERIFIER_REWARD), "Transfer to solver failed");
    }

    function withdrawFunds() external onlyOwner {
        require(usdc.transfer(owner(), usdc.balanceOf(address(this))), "Withdrawal failed");
    }
}
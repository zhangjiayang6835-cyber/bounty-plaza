// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BountyPlatform is Ownable {
    IERC20 public usdc;
    uint256 public constant SOLVER_REWARD = 90 * 10**6; // 0.90 USDC
    uint256 public constant VERIFIER_REWARD = 10 * 10**6; // 0.10 USDC
    uint256 public constant CLAIM_BOND = 10 * 10**6; // 0.10 USDC

    event FundingAdded(uint256 amount);
    event BountyBecameClaimable(uint256 bountyId);
    event BountySettled(uint256 bountyId, address solver, address verifier);

    struct Bounty {
        uint256 id;
        address creator;
        uint256 totalFunding;
        bool isClaimable;
        bool isSettled;
        address solver;
        address verifier;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function addFunding(uint256 bountyId) external {
        require(bounties[bountyId].creator!= address(0), "Bounty does not exist");
        require(!bounties[bountyId].isClaimable, "Bounty is already claimable");

        uint256 amount = usdc.allowance(msg.sender, address(this));
        require(amount > 0, "No funds provided");

        usdc.transferFrom(msg.sender, address(this), amount);
        bounties[bountyId].totalFunding += amount;

        emit FundingAdded(amount);

        if (bounties[bountyId].totalFunding >= SOLVER_REWARD) {
            bounties[bountyId].isClaimable = true;
            emit BountyBecameClaimable(bountyId);
        }
    }

    function createBounty() external onlyOwner {
        require(nextBountyId == 0, "Only one bounty can be created at a time");

        bounties[nextBountyId] = Bounty({
            id: nextBountyId,
            creator: msg.sender,
            totalFunding: 0,
            isClaimable: false,
            isSettled: false,
            solver: address(0),
            verifier: address(0)
        });

        nextBountyId++;
    }

    function claimBounty(uint256 bountyId, address solver, address verifier) external {
        require(bounties[bountyId].isClaimable, "Bounty is not claimable");
        require(bounties[bountyId].solver == address(0), "Bounty already claimed");

        bounties[bountyId].solver = solver;
        bounties[bountyId].verifier = verifier;

        usdc.transferFrom(solver, address(this), CLAIM_BOND);
    }

    function settleBounty(uint256 bountyId) external {
        Bounty storage bounty = bounties[bountyId];
        require(bounty.isClaimable, "Bounty is not claimable");
        require(bounty.solver!= address(0), "Bounty not claimed");
        require(bounty.verifier == msg.sender, "Caller is not the verifier");

        require(bounty.totalFunding >= SOLVER_REWARD, "Insufficient funding");

        usdc.transfer(bounty.solver, SOLVER_REWARD);
        usdc.transfer(bounty.verifier, VERIFIER_REWARD);
        usdc.transfer(bounty.solver, CLAIM_BOND); // Return the claim bond

        bounty.isSettled = true;

        emit BountySettled(bountyId, bounty.solver, bounty.verifier);
    }
}
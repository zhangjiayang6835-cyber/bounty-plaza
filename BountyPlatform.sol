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
        address creator;
        uint256 solverReward;
        uint256 verifierReward;
        bool isClaimable;
        bool isSettled;
        address claimer;
        uint256 deadline;
    }

    mapping(uint256 => Bounty) public bounties;
    uint256 public nextBountyId;

    event BountyCreated(uint256 indexed bountyId, address indexed creator);
    event BountyFunded(uint256 indexed bountyId, uint256 amount);
    event BountyClaimed(uint256 indexed bountyId, address indexed claimer);
    event BountySettled(uint256 indexed bountyId);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createBounty() external {
        require(nextBountyId > 0, "Bounty ID must be greater than 0");
        require(usdc.transferFrom(msg.sender, address(this), SOLVER_REWARD + VERIFIER_REWARD), "Transfer failed");

        bounties[nextBountyId] = Bounty({
            creator: msg.sender,
            solverReward: SOLVER_REWARD,
            verifierReward: VERIFIER_REWARD,
            isClaimable: false,
            isSettled: false,
            claimer: address(0),
            deadline: block.timestamp + 7 days
        });

        emit BountyCreated(nextBountyId, msg.sender);
        nextBountyId++;
    }

    function fundBounty(uint256 bountyId) external {
        require(bounties[bountyId].creator!= address(0), "Bounty does not exist");
        require(!bounties[bountyId].isClaimable, "Bounty is already claimable");
        require(usdc.transferFrom(msg.sender, address(this), SOLVER_REWARD), "Transfer failed");

        bounties[bountyId].solverReward += SOLVER_REWARD;
        if (bounties[bountyId].solverReward >= SOLVER_REWARD) {
            bounties[bountyId].isClaimable = true;
        }

        emit BountyFunded(bountyId, SOLVER_REWARD);
    }

    function claimBounty(uint256 bountyId) external {
        require(bounties[bountyId].isClaimable, "Bounty is not claimable");
        require(bounties[bountyId].claimer == address(0), "Bounty is already claimed");
        require(usdc.transferFrom(msg.sender, address(this), CLAIM_BOND), "Transfer failed");

        bounties[bountyId].claimer = msg.sender;

        emit BountyClaimed(bountyId, msg.sender);
    }

    function settleBounty(uint256 bountyId, bytes memory proof) external {
        require(bounties[bountyId].isClaimable, "Bounty is not claimable");
        require(bounties[bountyId].claimer!= address(0), "Bounty is not claimed");
        require(block.timestamp <= bounties[bountyId].deadline, "Bounty has expired");

        (address childBounty) = abi.decode(proof, (address));
        require(childBounty!= address(0), "Invalid proof");

        require(usdc.transfer(bounties[bountyId].claimer, bounties[bountyId].solverReward), "Transfer failed");
        require(usdc.transfer(owner(), bounties[bountyId].verifierReward), "Transfer failed");

        bounties[bountyId].isSettled = true;

        emit BountySettled(bountyId);
    }
}
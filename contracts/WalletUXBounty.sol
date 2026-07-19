// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract WalletUXBounty is Ownable {
    IERC20 public usdc;
    address public onchainTermsRegistry;
    uint256 public constant BOUNTY_AMOUNT = 1 * 10**6; // 1 USDC
    uint256 public constant PARENT_SOLVER_REWARD = 9 * 10**5; // 0.90 USDC
    uint256 public constant VERIFIER_REWARD = 1 * 10**5; // 0.10 USDC
    uint256 public constant CLAIM_BOND = 1 * 10**5; // 0.10 USDC

    event BountyCreated(address indexed creator, uint256 amount);
    event BountyFunded(address indexed funder, uint256 amount);
    event BountyClaimed(address indexed solver, uint256 amount);

    constructor(
        address _usdc,
        address _onchainTermsRegistry
    ) {
        usdc = IERC20(_usdc);
        onchainTermsRegistry = _onchainTermsRegistry;
    }

    struct Bounty {
        address creator;
        address solver;
        bool isFunded;
        bool isClaimed;
    }

    mapping(uint256 => Bounty) public bounties;

    function createBounty() external {
        require(usdc.balanceOf(msg.sender) >= CLAIM_BOND, "Insufficient USDC for claim bond");
        uint256 bountyId = bounties.length;
        bounties[bountyId] = Bounty({
            creator: msg.sender,
            solver: address(0),
            isFunded: false,
            isClaimed: false
        });
        emit BountyCreated(msg.sender, BOUNTY_AMOUNT);
    }

    function fundBounty(uint256 bountyId) external {
        require(bounties[bountyId].creator == msg.sender, "Only the creator can fund the bounty");
        require(!bounties[bountyId].isFunded, "Bounty is already funded");
        require(usdc.transferFrom(msg.sender, address(this), BOUNTY_AMOUNT), "Transfer failed");
        bounties[bountyId].isFunded = true;
        emit BountyFunded(msg.sender, BOUNTY_AMOUNT);
    }

    function registerSolver(uint256 bountyId, address solver) external {
        require(bounties[bountyId].creator == msg.sender, "Only the creator can register a solver");
        require(bounties[bountyId].solver == address(0), "Solver is already registered");
        bounties[bountyId].solver = solver;
    }

    function claimBounty(uint256 bountyId) external {
        require(bounties[bountyId].solver == msg.sender, "Only the registered solver can claim the bounty");
        require(bounties[bountyId].isFunded, "Bounty must be funded before claiming");
        require(!bounties[bountyId].isClaimed, "Bounty has already been claimed");

        // Transfer the bounty amount to the solver
        require(usdc.transfer(bounties[bountyId].solver, BOUNTY_AMOUNT - PARENT_SOLVER_REWARD - VERIFIER_REWARD), "Transfer to solver failed");

        // Transfer the parent solver reward to the creator
        require(usdc.transfer(bounties[bountyId].creator, PARENT_SOLVER_REWARD), "Transfer to creator failed");

        // Transfer the verifier reward to the verifier (assuming the verifier is the contract owner)
        require(usdc.transfer(owner(), VERIFIER_REWARD), "Transfer to verifier failed");

        bounties[bountyId].isClaimed = true;
        emit BountyClaimed(bounties[bountyId].solver, BOUNTY_AMOUNT);
    }

    function withdrawClaimBond(uint256 bountyId) external {
        require(bounties[bountyId].creator == msg.sender, "Only the creator can withdraw the claim bond");
        require(bounties[bountyId].isClaimed, "Bounty must be claimed before withdrawing the claim bond");
        require(usdc.transfer(msg.sender, CLAIM_BOND), "Transfer of claim bond failed");
    }
}
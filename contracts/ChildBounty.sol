// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ChildBounty is Ownable {
    IERC20 public usdc;
    address public parentBounty;
    uint256 public parentBountyId;
    uint256 public parentBountyRound;
    address public canonicalChildVerifier;
    uint256 public solverReward;
    uint256 public verifierReward;
    uint256 public claimBond;
    bool public isClaimable;
    bool public isFunded;
    address public creator;
    address public claimer;

    event FundingAdded(uint256 amount);
    event BountyBecameClaimable();
    event BountySettled(address indexed claimer);

    constructor(
        address _usdc,
        address _parentBounty,
        uint256 _parentBountyId,
        uint256 _parentBountyRound,
        address _canonicalChildVerifier,
        uint256 _solverReward,
        uint256 _verifierReward,
        uint256 _claimBond
    ) {
        usdc = IERC20(_usdc);
        parentBounty = _parentBounty;
        parentBountyId = _parentBountyId;
        parentBountyRound = _parentBountyRound;
        canonicalChildVerifier = _canonicalChildVerifier;
        solverReward = _solverReward;
        verifierReward = _verifierReward;
        claimBond = _claimBond;
        creator = msg.sender;
    }

    modifier onlyCreator() {
        require(msg.sender == creator, "Only the creator can call this function");
        _;
    }

    modifier onlyCanonicalChildVerifier() {
        require(msg.sender == canonicalChildVerifier, "Only the canonical child verifier can call this function");
        _;
    }

    function fundBounty() external payable onlyCreator {
        require(!isFunded, "Bounty is already funded");
        require(usdc.transferFrom(msg.sender, address(this), solverReward + verifierReward + claimBond), "Transfer failed");
        isFunded = true;
        emit FundingAdded(solverReward + verifierReward + claimBond);
    }

    function makeBountyClaimable() external onlyCreator {
        require(isFunded, "Bounty must be funded first");
        isClaimable = true;
        emit BountyBecameClaimable();
    }

    function claimBounty() external {
        require(isClaimable, "Bounty is not claimable yet");
        require(claimer == address(0), "Bounty has already been claimed");
        require(msg.sender!= creator, "Creator cannot claim the bounty");

        claimer = msg.sender;
        usdc.transfer(claimer, solverReward - claimBond); // Transfer reward minus claim bond

        bytes memory proof = abi.encode(address(this));
        (bool success, ) = canonicalChildVerifier.call(abi.encodeWithSignature("verifyAndSettle(bytes)", proof));
        require(success, "Verification and settlement failed");

        emit BountySettled(claimer);
    }

    function refundClaimBond() external onlyCanonicalChildVerifier {
        require(claimer!= address(0), "Bounty has not been claimed yet");
        usdc.transfer(claimer, claimBond); // Refund claim bond to the claimer
    }
}
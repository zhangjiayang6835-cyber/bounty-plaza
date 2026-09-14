// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title BatchYieldHarvester
 * @notice Production-grade yield harvesting and asset transfer coordinator.
 * @dev Employs SafeERC20 wrapper across all asset transfer hooks to support standard and non-standard tokens.
 */
contract BatchYieldHarvester {
    using SafeERC20 for IERC20;

    address public immutable owner;

    error LengthMismatch();
    error ZeroAddress();
    error ZeroAmount();
    error InsufficientBalance(address token, uint256 available, uint256 requested);
    error Unauthorized();

    event AssetDeposited(address indexed token, address indexed sender, uint256 amount);
    event AssetWithdrawn(address indexed token, address indexed recipient, uint256 amount);
    event YieldHarvested(address indexed token, address indexed recipient, uint256 amount);
    event BatchHarvestCompleted(uint256 totalTransfers);
    event YieldReinvested(address indexed token, address indexed strategy, uint256 amount);

    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    function _checkOwner() internal view {
        if (msg.sender != owner) {
            revert Unauthorized();
        }
    }

    /**
     * @notice Initializes the yield harvester with deployer as owner.
     */
    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Deposits asset into the harvester using safe transfer hook.
     * @param token Address of ERC-20 token.
     * @param amount Units of token to deposit.
     */
    function depositAsset(IERC20 token, uint256 amount) external {
        if (address(token) == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        token.safeTransferFrom(msg.sender, address(this), amount);
        emit AssetDeposited(address(token), msg.sender, amount);
    }

    /**
     * @notice Harvests yield for a single recipient using safe transfer hook.
     * @param token Address of ERC-20 token.
     * @param recipient Target recipient of the harvested yield.
     * @param amount Units of yield to transfer.
     */
    function harvestYield(IERC20 token, address recipient, uint256 amount) public onlyOwner {
        if (address(token) == address(0)) revert ZeroAddress();
        if (recipient == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        uint256 balance = token.balanceOf(address(this));
        if (balance < amount) {
            revert InsufficientBalance(address(token), balance, amount);
        }

        token.safeTransfer(recipient, amount);
        emit YieldHarvested(address(token), recipient, amount);
    }

    /**
     * @notice Executes batch yield harvesting across multiple tokens and recipients.
     * @dev Operates atomically; reverts if any individual transfer hook fails.
     * @param tokens Array of ERC-20 token contracts.
     * @param recipients Array of yield beneficiary addresses.
     * @param amounts Array of token quantities to harvest.
     */
    function batchHarvestYield(
        IERC20[] calldata tokens,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner {
        uint256 length = tokens.length;
        if (length != recipients.length || length != amounts.length) {
            revert LengthMismatch();
        }

        for (uint256 i = 0; i < length; i++) {
            harvestYield(tokens[i], recipients[i], amounts[i]);
        }

        emit BatchHarvestCompleted(length);
    }

    /**
     * @notice Withdraws protocol assets to specified destination.
     * @param token Address of ERC-20 token.
     * @param to Destination address.
     * @param amount Quantity of tokens to withdraw.
     */
    function withdrawAsset(IERC20 token, address to, uint256 amount) external onlyOwner {
        if (address(token) == address(0)) revert ZeroAddress();
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        uint256 balance = token.balanceOf(address(this));
        if (balance < amount) {
            revert InsufficientBalance(address(token), balance, amount);
        }

        token.safeTransfer(to, amount);
        emit AssetWithdrawn(address(token), to, amount);
    }

    /**
     * @notice Generic transfer asset hook protecting internal transfers.
     * @param token Address of ERC-20 token.
     * @param to Recipient address.
     * @param amount Units of token.
     */
    function transferAssetHook(IERC20 token, address to, uint256 amount) external onlyOwner {
        if (address(token) == address(0)) revert ZeroAddress();
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        token.safeTransfer(to, amount);
    }

    /**
     * @notice Approves and reinvests yield into external strategy using forceApprove.
     * @param token Address of ERC-20 token.
     * @param strategy Target strategy address.
     * @param amount Amount to approve.
     */
    function reinvestYield(IERC20 token, address strategy, uint256 amount) external onlyOwner {
        if (address(token) == address(0)) revert ZeroAddress();
        if (strategy == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        token.forceApprove(strategy, amount);
        emit YieldReinvested(address(token), strategy, amount);
    }
}

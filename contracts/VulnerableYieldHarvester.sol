// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title VulnerableYieldHarvester
 * @notice Demonstrates unchecked return value vulnerability in ERC-20 transfer callbacks.
 * @dev Direct calls to transfer() revert when interacting with non-standard tokens like USDT.
 */
contract VulnerableYieldHarvester {
    address public immutable owner;

    error LengthMismatch();
    error TransferFailed();
    error Unauthorized();

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
     * @notice Initializes vulnerable harvester.
     */
    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Harvests yield using direct transfer call expecting bool return.
     * @param token Address of ERC-20 token.
     * @param recipient Target recipient.
     * @param amount Units to transfer.
     */
    function harvestYieldDirect(IERC20 token, address recipient, uint256 amount) public onlyOwner {
        bool success = token.transfer(recipient, amount);
        if (!success) {
            revert TransferFailed();
        }
    }

    /**
     * @notice Batch harvests yield using direct transfer calls.
     * @dev Reverts if any token does not return standard 32-byte boolean.
     * @param tokens Array of tokens.
     * @param recipients Array of recipients.
     * @param amounts Array of amounts.
     */
    function batchHarvestYieldDirect(
        IERC20[] calldata tokens,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner {
        uint256 length = tokens.length;
        if (length != recipients.length || length != amounts.length) {
            revert LengthMismatch();
        }

        for (uint256 i = 0; i < length; i++) {
            harvestYieldDirect(tokens[i], recipients[i], amounts[i]);
        }
    }
}

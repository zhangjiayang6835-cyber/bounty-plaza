// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface IVaultDepositTarget {
    function deposit(uint256 assets, address receiver) external returns (uint256);
}

/**
 * @title ReentrantERC20
 * @notice ERC20 token designed to execute reentrancy attempts against a target vault during token transfers.
 */
contract ReentrantERC20 is ERC20 {
    address public targetVault;
    bool public attackOnTransferFrom;
    bool private _inAttack;

    /**
     * @notice Initializes the reentrant test token.
     */
    constructor() ERC20("Reentrant Token", "rTOKEN") {}

    /**
     * @notice Sets the target vault address for reentrancy testing.
     * @param vault The address of the vault to target.
     */
    function setTargetVault(address vault) external {
        targetVault = vault;
    }

    /**
     * @notice Enables or disables reentrant execution on transferFrom calls.
     * @param enabled Boolean flag to toggle attack behavior.
     */
    function setAttackOnTransferFrom(bool enabled) external {
        attackOnTransferFrom = enabled;
    }

    /**
     * @notice Mints tokens to a designated recipient address.
     * @param to The recipient address.
     * @param amount The token amount to mint.
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @notice Overridden transferFrom that attempts to reenter target vault when enabled.
     * @param sender The token owner.
     * @param recipient The token recipient.
     * @param amount The transfer amount.
     * @return Boolean indicating success.
     */
    function transferFrom(
        address sender,
        address recipient,
        uint256 amount
    ) public virtual override returns (bool) {
        if (attackOnTransferFrom && !_inAttack && targetVault != address(0)) {
            _inAttack = true;
            IVaultDepositTarget(targetVault).deposit(1, address(this));
            _inAttack = false;
        }
        return super.transferFrom(sender, recipient, amount);
    }
}

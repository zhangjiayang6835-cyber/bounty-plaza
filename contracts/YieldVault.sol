// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title YieldVault
 * @notice ERC-4626 compliant yield vault with decimal offset protection against donation and inflation attacks, and reentrancy guards on all external asset transfer routines.
 */
contract YieldVault is ERC4626, ReentrancyGuard {
    uint8 private constant DECIMALS_OFFSET = 3;

    /**
     * @notice Initializes the YieldVault with an underlying asset token and vault share metadata.
     * @param asset_ The underlying ERC20 asset token.
     */
    constructor(IERC20 asset_)
        ERC4626(asset_)
        ERC20("Yield Vault Shares", "yvToken")
    {}

    /**
     * @notice Returns the decimals offset used to calculate virtual shares and assets.
     * @dev Mitigates inflation and donation attacks by creating virtual shares that offset initial deposit ratios.
     * @return Offset value in decimals.
     */
    function _decimalsOffset() internal view virtual override returns (uint8) {
        return DECIMALS_OFFSET;
    }

    /**
     * @notice Returns the public decimals offset value.
     * @return The decimals offset value configured for virtual shares.
     */
    function decimalsOffset() external pure returns (uint8) {
        return DECIMALS_OFFSET;
    }

    /**
     * @notice Deposits assets into the vault with reentrancy protection.
     * @param assets The amount of assets to deposit.
     * @param receiver The address receiving the minted shares.
     * @return shares The amount of shares minted.
     */
    function deposit(uint256 assets, address receiver)
        public
        virtual
        override
        nonReentrant
        returns (uint256 shares)
    {
        return super.deposit(assets, receiver);
    }

    /**
     * @notice Mints shares by depositing assets with reentrancy protection.
     * @param shares The amount of shares to mint.
     * @param receiver The address receiving the minted shares.
     * @return assets The amount of assets deposited.
     */
    function mint(uint256 shares, address receiver)
        public
        virtual
        override
        nonReentrant
        returns (uint256 assets)
    {
        return super.mint(shares, receiver);
    }

    /**
     * @notice Withdraws assets from the vault with reentrancy protection.
     * @param assets The amount of assets to withdraw.
     * @param receiver The address receiving the assets.
     * @param owner The address owning the burned shares.
     * @return shares The amount of shares burned.
     */
    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    )
        public
        virtual
        override
        nonReentrant
        returns (uint256 shares)
    {
        return super.withdraw(assets, receiver, owner);
    }

    /**
     * @notice Redeems shares for assets from the vault with reentrancy protection.
     * @param shares The amount of shares to redeem.
     * @param receiver The address receiving the assets.
     * @param owner The address owning the burned shares.
     * @return assets The amount of assets redeemed.
     */
    function redeem(
        uint256 shares,
        address receiver,
        address owner
    )
        public
        virtual
        override
        nonReentrant
        returns (uint256 assets)
    {
        return super.redeem(shares, receiver, owner);
    }
}

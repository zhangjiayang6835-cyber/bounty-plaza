// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title YieldVault
 * @dev ERC-4626 compliant vault with virtual share/asset offsets and reentrancy protection.
 */
contract YieldVault is ERC20, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Math for uint256;

    IERC20 private immutable _asset;
    uint8 private immutable _underlyingDecimals;

    error ZeroAmount();
    error ZeroShares();
    error SlippageExceeded();

    constructor(IERC20 asset_, string memory name_, string memory symbol_)
        ERC20(name_, symbol_)
    {
        _asset = asset_;
        _underlyingDecimals = 18; // Default ERC20 decimals
    }

    /** @notice Returns the address of the underlying asset. */
    function asset() public view returns (address) {
        return address(_asset);
    }

    /** @notice Total amount of underlying assets held by the vault. */
    function totalAssets() public view returns (uint256) {
        return _asset.balanceOf(address(this));
    }

    /**
     * @dev Decimal offset for virtual shares / virtual assets to eliminate inflation attacks.
     * Returns the number of decimal places for the virtual share offset.
     * A value of 3 means an offset of 10**3 = 1,000 virtual shares.
     */
    function _decimalsOffset() internal pure virtual returns (uint8) {
        return 3;
    }

    /** @notice Convert a given amount of assets to shares using virtual offsets. */
    function convertToShares(uint256 assets) public view returns (uint256) {
        return Math.mulDiv(
            assets,
            totalSupply() + 10 ** _decimalsOffset(),
            totalAssets() + 1,
            Math.Rounding.Floor
        );
    }

    /** @notice Convert a given amount of shares to assets using virtual offsets. */
    function convertToAssets(uint256 shares) public view returns (uint256) {
        return Math.mulDiv(
            shares,
            totalAssets() + 1,
            totalSupply() + 10 ** _decimalsOffset(),
            Math.Rounding.Floor
        );
    }

    /**
     * @notice Deposit assets and mint protected shares.
     * @param assets Amount of underlying assets to deposit.
     * @param receiver Address that will receive the minted shares.
     * @return shares Number of shares minted.
     */
    function deposit(uint256 assets, address receiver) external nonReentrant returns (uint256 shares) {
        if (assets == 0) revert ZeroAmount();

        _asset.safeTransferFrom(msg.sender, address(this), assets);

        shares = convertToShares(assets);
        if (shares == 0) revert ZeroShares();

        _mint(receiver, shares);
    }

    /**
     * @notice Mint a specific amount of shares by providing enough assets.
     * @param shares Number of shares to mint.
     * @param receiver Address that will receive the minted shares.
     * @return assets Amount of assets transferred from the caller.
     */
    function mint(uint256 shares, address receiver) external nonReentrant returns (uint256 assets) {
        if (shares == 0) revert ZeroShares();

        assets = convertToAssets(shares);
        if (assets == 0) revert ZeroAmount();

        _asset.safeTransferFrom(msg.sender, address(this), assets);
        _mint(receiver, shares);
    }

    /**
     * @notice Withdraw assets by burning shares.
     * @param assets Amount of assets to withdraw.
     * @param receiver Address that will receive the assets.
     * @param owner Owner of the shares being burned.
     * @return shares Number of shares burned.
     */
    function withdraw(uint256 assets, address receiver, address owner) external nonReentrant returns (uint256 shares) {
        if (assets == 0) revert ZeroAmount();

        shares = convertToShares(assets);
        if (shares == 0) revert ZeroShares();

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        _burn(owner, shares);
        _asset.safeTransfer(receiver, assets);
    }

    /**
     * @notice Redeem shares for underlying assets.
     * @param shares Number of shares to redeem.
     * @param receiver Address that will receive the assets.
     * @param owner Owner of the shares being redeemed.
     * @return assets Amount of assets transferred to the receiver.
     */
    function redeem(uint256 shares, address receiver, address owner) external nonReentrant returns (uint256 assets) {
        if (shares == 0) revert ZeroShares();

        assets = convertToAssets(shares);
        if (assets == 0) revert ZeroAmount();

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        _burn(owner, shares);
        _asset.safeTransfer(receiver, assets);
    }
}

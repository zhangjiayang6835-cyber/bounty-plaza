// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {ERC20, IERC4626} from "./YieldVault.sol";

/**
 * @title YieldVaultVulnerable
 * @notice The ORIGINAL audited vault, kept for regression testing only.
 *
 * Reproduces the two critical flaws fixed by `YieldVault`:
 *  1. Share inflation: share math is `assets * totalSupply / totalAssets`
 *     (rounding down, with a short-circuit for the first deposit), so an
 *     attacker can deposit 1 wei, donate assets directly to the contract and
 *     force every subsequent depositor to round down to zero shares.
 *  2. No reentrancy guard on `deposit`/`withdraw`/`redeem`, so an ERC777-style
 *     asset can re-enter the vault during `transfer`/`transferFrom`.
 *
 * Deploy with `offset_ = 0`; it does NOT use the hardened conversion math.
 */
contract YieldVaultVulnerable is ERC20, IERC4626 {
    IERC20Internal immutable _asset;

    constructor(address asset_, string memory name_, string memory symbol_) ERC20(name_, symbol_) {
        require(asset_ != address(0), "YieldVault: zero asset address");
        _asset = IERC20Internal(asset_);
    }

    function asset() external view virtual returns (address) {
        return address(_asset);
    }

    function totalAssets() public view virtual returns (uint256) {
        return _asset.balanceOf(address(this));
    }

    /// @dev Flawed shares -> assets conversion (rounds down, no virtual shares).
    function _convertToShares(uint256 assets) internal view virtual returns (uint256) {
        uint256 supply = totalSupply();
        uint256 total = totalAssets();
        if (supply == 0 || total == 0) {
            return assets;
        }
        return assets * supply / total;
    }

    /// @dev Flawed shares -> assets conversion (no virtual shares).
    function _convertToAssets(uint256 shares) internal view virtual returns (uint256) {
        uint256 supply = totalSupply();
        uint256 total = totalAssets();
        if (supply == 0 || total == 0) {
            return shares;
        }
        return shares * total / supply;
    }

    function convertToShares(uint256 assets) public view virtual returns (uint256) {
        return _convertToShares(assets);
    }

    function convertToAssets(uint256 shares) public view virtual returns (uint256) {
        return _convertToAssets(shares);
    }

    function previewDeposit(uint256 assets) public view virtual returns (uint256) {
        return _convertToShares(assets);
    }

    function previewMint(uint256 shares) public view virtual returns (uint256) {
        return _convertToAssets(shares);
    }

    function previewWithdraw(uint256 assets) public view virtual returns (uint256) {
        return _convertToAssets(assets);
    }

    function previewRedeem(uint256 shares) public view virtual returns (uint256) {
        return _convertToShares(shares);
    }

    function maxDeposit(address) public view virtual returns (uint256) {
        return type(uint256).max;
    }

    function maxMint(address) public view virtual returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(address owner) public view virtual returns (uint256) {
        return _convertToAssets(balanceOf(owner));
    }

    function maxRedeem(address owner) public view virtual returns (uint256) {
        return balanceOf(owner);
    }

    // NOTE: no nonReentrant modifier here (this is the vulnerable reference).
    function deposit(uint256 assets, address receiver) public virtual returns (uint256) {
        uint256 maxAssets = maxDeposit(receiver);
        require(assets <= maxAssets, "ERC4626: deposit more than max");

        uint256 shares = previewDeposit(assets);
        _deposit(msg.sender, receiver, assets, shares);

        return shares;
    }

    function mint(uint256 shares, address receiver) public virtual returns (uint256) {
        uint256 maxShares = maxMint(receiver);
        require(shares <= maxShares, "ERC4626: mint more than max");

        uint256 assets = previewMint(shares);
        _deposit(msg.sender, receiver, assets, shares);

        return assets;
    }

    function withdraw(uint256 assets, address receiver, address owner) public virtual returns (uint256) {
        uint256 maxAssets = maxWithdraw(owner);
        require(assets <= maxAssets, "ERC4626: withdraw more than max");

        uint256 shares = previewWithdraw(assets);
        _withdraw(msg.sender, receiver, owner, assets, shares);

        return shares;
    }

    function redeem(uint256 shares, address receiver, address owner) public virtual returns (uint256) {
        uint256 maxShares = maxRedeem(owner);
        require(shares <= maxShares, "ERC4626: redeem more than max");

        uint256 assets = previewRedeem(shares);
        _withdraw(msg.sender, receiver, owner, assets, shares);

        return assets;
    }

    function _deposit(address caller, address receiver, uint256 assets, uint256 shares) internal virtual {
        bool ok = _asset.transferFrom(caller, address(this), assets);
        require(ok, "ERC4626: transferFrom failed");

        _mint(receiver, shares);

        emit Deposit(caller, receiver, assets, shares);
    }

    function _withdraw(address caller, address receiver, address owner, uint256 assets, uint256 shares)
        internal
        virtual
    {
        if (caller != owner) {
            _spendAllowance(owner, caller, shares);
        }

        _burn(owner, shares);

        bool ok = _asset.transfer(receiver, assets);
        require(ok, "ERC4626: transfer failed");

        emit Withdraw(caller, receiver, owner, assets, shares);
    }
}

interface IERC20Internal {
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}
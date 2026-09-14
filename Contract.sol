// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract YieldVault is ERC20, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Math for uint256;

    IERC20 private immutable _asset;
    uint8 private immutable _underlyingDecimals;

    error ZeroAmount();
    error ZeroShares();

    constructor(IERC20 asset_, string memory name_, string memory symbol_) 
        ERC20(name_, symbol_) 
    {
        _asset = asset_;
        _underlyingDecimals = 18; 
    }

    function asset() public view returns (address) {
        return address(_asset);
    }

    function totalAssets() public view returns (uint256) {
        return _asset.balanceOf(address(this));
    }

    /** 
     * @dev Enforces decimal offset for virtual shares to eliminate inflation attacks. 
     */
    function _decimalsOffset() internal pure virtual returns (uint8) {
        return 3; // Virtual shares offset factor = 10^3 = 1000
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        return Math.mulDiv(
            assets,
            totalSupply() + 10 ** _decimalsOffset(),
            totalAssets() + 1,
            Math.Rounding.Floor
        );
    }

    function convertToAssets(uint256 shares) public view returns (uint256) {
        return Math.mulDiv(
            shares,
            totalAssets() + 1,
            totalSupply() + 10 ** _decimalsOffset(),
            Math.Rounding.Floor
        );
    }

    /** 
     * @notice Deposit assets and mint protected shares 
     */
    function deposit(uint256 assets, address receiver) external nonReentrant returns (uint256 shares) {
        if (assets == 0) revert ZeroAmount();

        shares = convertToShares(assets);
        if (shares == 0) revert ZeroShares();

        _asset.safeTransferFrom(msg.sender, address(this), assets);
        _mint(receiver, shares);
    }

    /** 
     * @notice Redeem shares for underlying assets 
     */
    function redeem(uint256 shares, address receiver, address owner) external nonReentrant returns (uint256 assets) {
        if (shares == 0) revert ZeroAmount();
        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        assets = convertToAssets(shares);
        if (assets == 0) revert ZeroAmount();

        _burn(owner, shares);
        _asset.safeTransfer(receiver, assets);
    }
}

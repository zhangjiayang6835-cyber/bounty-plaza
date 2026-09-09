// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC3156FlashLender} from "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import {IERC3156FlashBorrower} from "@openzeppelin/contracts/interfaces/IERC3156FlashBorrower.sol";
import {Math} from "./libraries/Math.sol";

/**
 * @title FlashVault
 * @notice ERC-3156 compliant vault and flash lender with upward fee rounding and strict reserve preservation.
 */
contract FlashVault is IERC3156FlashLender, ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    using Math for uint256;

    uint256 public constant FEE_PRECISION = 10_000;
    bytes32 public constant CALLBACK_SUCCESS = keccak256("ERC3156FlashBorrower.onFlashLoan");

    IERC20 public immutable ASSET;
    uint256 public feeRate;
    uint256 public minFee;

    error UnsupportedToken(address token);
    error ExceedsMaxLoan(uint256 requested, uint256 available);
    error ZeroAmountLoan();
    error CallbackFailed();
    error InsufficientRepayment(uint256 expectedBalance, uint256 actualBalance);

    event FlashLoan(
        address indexed receiver,
        address indexed token,
        uint256 amount,
        uint256 fee
    );
    event FeeRateUpdated(uint256 oldRate, uint256 newRate);
    event MinFeeUpdated(uint256 oldMinFee, uint256 newMinFee);

    /**
     * @notice Initializes the flash loan vault with underlying asset and fee parameters.
     * @param asset_ The underlying asset token managed by the vault.
     * @param feeRate_ Fee rate in basis points.
     * @param minFee_ Minimum fee unit floor for micro-drainage prevention.
     */
    constructor(
        IERC20 asset_,
        uint256 feeRate_,
        uint256 minFee_
    ) Ownable(msg.sender) {
        ASSET = asset_;
        feeRate = feeRate_;
        minFee = minFee_ > 0 ? minFee_ : 1;
    }

    /**
     * @notice Returns the underlying asset token address.
     * @return Underlying token address.
     */
    function asset() external view returns (address) {
        return address(ASSET);
    }

    /**
     * @notice Updates the flash loan fee rate.
     * @param newRate New fee rate in basis points.
     */
    function setFeeRate(uint256 newRate) external onlyOwner {
        emit FeeRateUpdated(feeRate, newRate);
        feeRate = newRate;
    }

    /**
     * @notice Updates the minimum fee floor.
     * @param newMinFee New minimum fee threshold.
     */
    function setMinFee(uint256 newMinFee) external onlyOwner {
        emit MinFeeUpdated(minFee, newMinFee);
        minFee = newMinFee;
    }

    /**
     * @notice Returns maximum borrowable amount for a given token.
     * @param token Address of the queried token.
     * @return Maximum amount available for flash lending.
     */
    function maxFlashLoan(address token) external view override returns (uint256) {
        if (token != address(ASSET)) {
            return 0;
        }
        return ASSET.balanceOf(address(this));
    }

    /**
     * @notice Computes flash loan fee using Math.mulDiv with Rounding.Up and zero-fee prevention.
     * @param token Address of the token.
     * @param amount Principal borrowed amount.
     * @return fee Upward-rounded fee required for loan.
     */
    function flashFee(address token, uint256 amount) public view override returns (uint256) {
        if (token != address(ASSET)) {
            revert UnsupportedToken(token);
        }
        if (amount == 0) {
            revert ZeroAmountLoan();
        }
        if (feeRate == 0) {
            return 0;
        }

        uint256 fee = Math.mulDiv(amount, feeRate, FEE_PRECISION, Math.Rounding.Up);

        if (fee == 0) {
            fee = 1;
        }
        if (fee < minFee) {
            fee = minFee;
        }

        return fee;
    }

    /**
     * @notice Executes an ERC-3156 flash loan with reentrancy protection and reserve verification.
     * @param receiver Recipient of the flash loan and target of the callback.
     * @param token Address of the lent token.
     * @param amount Principal loan amount.
     * @param data Forwarded payload for the callback.
     * @return True if flash loan succeeded.
     */
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) external override nonReentrant returns (bool) {
        uint256 fee = flashFee(token, amount);
        uint256 maxAvailable = ASSET.balanceOf(address(this));

        if (amount > maxAvailable) {
            revert ExceedsMaxLoan(amount, maxAvailable);
        }

        uint256 balanceBefore = maxAvailable;

        ASSET.safeTransfer(address(receiver), amount);

        bytes32 callbackResult = receiver.onFlashLoan(msg.sender, token, amount, fee, data);
        if (callbackResult != CALLBACK_SUCCESS) {
            revert CallbackFailed();
        }

        ASSET.safeTransferFrom(address(receiver), address(this), amount + fee);

        uint256 balanceAfter = ASSET.balanceOf(address(this));
        if (balanceAfter < balanceBefore + fee) {
            revert InsufficientRepayment(balanceBefore + fee, balanceAfter);
        }

        emit FlashLoan(address(receiver), token, amount, fee);
        return true;
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC3156FlashBorrower} from "@openzeppelin/contracts/interfaces/IERC3156FlashBorrower.sol";
import {IERC3156FlashLender} from "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import {Math} from "./libraries/Math.sol";

/**
 * @title FlashBorrower
 * @notice ERC-3156 compliant flash borrower with upward-rounded fee calculation and zero-fee exploit prevention.
 */
contract FlashBorrower is IERC3156FlashBorrower, Ownable {
    using Math for uint256;

    uint256 public constant FEE_PRECISION = 10_000;
    bytes32 public constant CALLBACK_SUCCESS = keccak256("ERC3156FlashBorrower.onFlashLoan");

    uint256 public feeRate;
    uint256 public minFee;
    IERC3156FlashLender public lender;

    error ZeroAmountLoan();
    error InvalidLender();
    error InvalidInitiator();
    error ZeroFeeNotAllowed();
    error FlashLoanFailed();

    event FlashLoanExecuted(address indexed token, uint256 amount, uint256 fee);
    event FeeRateUpdated(uint256 oldRate, uint256 newRate);
    event MinFeeUpdated(uint256 oldMinFee, uint256 newMinFee);
    event LenderUpdated(address indexed oldLender, address indexed newLender);

    /**
     * @notice Initializes the FlashBorrower contract with owner, lender, fee rate, and minimum fee.
     * @param lender_ The trusted flash lender contract address.
     * @param feeRate_ Initial fee rate in basis points (1 bp = 0.01%).
     * @param minFee_ Minimum fee unit threshold for zero-fee prevention.
     */
    constructor(
        IERC3156FlashLender lender_,
        uint256 feeRate_,
        uint256 minFee_
    ) Ownable(msg.sender) {
        lender = lender_;
        feeRate = feeRate_;
        minFee = minFee_ > 0 ? minFee_ : 1;
    }

    /**
     * @notice Updates the flash loan fee rate.
     * @param newFeeRate New fee rate in basis points.
     */
    function setFeeRate(uint256 newFeeRate) external onlyOwner {
        emit FeeRateUpdated(feeRate, newFeeRate);
        feeRate = newFeeRate;
    }

    /**
     * @notice Updates the minimum fee floor.
     * @param newMinFee New minimum fee in token units.
     */
    function setMinFee(uint256 newMinFee) external onlyOwner {
        emit MinFeeUpdated(minFee, newMinFee);
        minFee = newMinFee;
    }

    /**
     * @notice Updates the trusted lender contract.
     * @param newLender New lender address.
     */
    function setLender(IERC3156FlashLender newLender) external onlyOwner {
        emit LenderUpdated(address(lender), address(newLender));
        lender = newLender;
    }

    /**
     * @notice Computes expected flash loan fee using Math.mulDiv with Rounding.Up and zero-fee prevention.
     * @param token Address of the borrowed asset token.
     * @param amount Principal loan amount.
     * @return fee Upward-rounded fee amount owed to vault reserves.
     */
    function flashLoanFee(address token, uint256 amount) public view returns (uint256) {
        token;
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
     * @notice Pure fee computation helper using Math.mulDiv with Rounding.Up and zero-fee prevention.
     * @param amount Principal loan amount.
     * @param rate Fee rate in basis points.
     * @return fee Upward-rounded fee amount.
     */
    function calculateFee(uint256 amount, uint256 rate) public view returns (uint256) {
        if (amount == 0 || rate == 0) {
            return 0;
        }

        uint256 fee = Math.mulDiv(amount, rate, FEE_PRECISION, Math.Rounding.Up);

        if (fee == 0) {
            fee = 1;
        }
        if (fee < minFee) {
            fee = minFee;
        }

        return fee;
    }

    /**
     * @notice Initiates a flash loan through the configured lender.
     * @param token Address of the borrowed token.
     * @param amount Principal loan amount.
     * @param data Arbitrary payload forwarded to onFlashLoan.
     * @return success True if flash loan succeeded.
     */
    function executeFlashLoan(
        address token,
        uint256 amount,
        bytes calldata data
    ) external onlyOwner returns (bool) {
        if (amount == 0) {
            revert ZeroAmountLoan();
        }
        if (address(lender) == address(0)) {
            revert InvalidLender();
        }

        bool success = lender.flashLoan(this, token, amount, data);
        if (!success) {
            revert FlashLoanFailed();
        }
        return true;
    }

    /**
     * @notice ERC-3156 flash loan callback invoked by the lender.
     * @param initiator Originator of the flash loan request.
     * @param token Address of the lent asset.
     * @param amount Principal loan amount.
     * @param fee Additional fee charged by the lender.
     * @param data Arbitrary payload from initiator.
     * @return Return value confirming execution success.
     */
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external override returns (bytes32) {
        data;
        if (address(lender) != address(0) && msg.sender != address(lender)) {
            revert InvalidLender();
        }
        if (initiator != address(this) && initiator != owner()) {
            revert InvalidInitiator();
        }
        if (amount > 0 && feeRate > 0 && fee == 0) {
            revert ZeroFeeNotAllowed();
        }

        IERC20(token).approve(msg.sender, amount + fee);
        emit FlashLoanExecuted(token, amount, fee);

        return CALLBACK_SUCCESS;
    }
}

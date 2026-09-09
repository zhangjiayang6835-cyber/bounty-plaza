// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math as OZMath} from "@openzeppelin/contracts/utils/math/Math.sol";

/**
 * @title Math
 * @notice Standard math utility library supporting high-precision 512-bit intermediate multiplication and division with directional rounding.
 */
library Math {
    enum Rounding {
        Down,
        Up,
        Zero,
        Floor,
        Ceil
    }

    /**
     * @notice Calculates floor(x * y / denominator) with full precision.
     * @param x Multiplicand.
     * @param y Multiplier.
     * @param denominator Divisor.
     * @return Result of division rounded down.
     */
    function mulDiv(
        uint256 x,
        uint256 y,
        uint256 denominator
    ) internal pure returns (uint256) {
        return OZMath.mulDiv(x, y, denominator, OZMath.Rounding.Floor);
    }

    /**
     * @notice Calculates (x * y) / denominator with full 512-bit precision and explicit directional rounding.
     * @param x Multiplicand.
     * @param y Multiplier.
     * @param denominator Divisor.
     * @param rounding Rounding direction.
     * @return Result of division according to rounding mode.
     */
    function mulDiv(
        uint256 x,
        uint256 y,
        uint256 denominator,
        Rounding rounding
    ) internal pure returns (uint256) {
        OZMath.Rounding ozRounding = (rounding == Rounding.Up || rounding == Rounding.Ceil)
            ? OZMath.Rounding.Ceil
            : OZMath.Rounding.Floor;
        return OZMath.mulDiv(x, y, denominator, ozRounding);
    }
}

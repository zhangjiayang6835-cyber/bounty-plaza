// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title RevertingERC20
 * @notice Mock token that intentionally reverts on transfer operations.
 */
contract RevertingERC20 {
    string public name;
    string public symbol;
    uint8 public immutable decimals;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    error TransferBlocked();

    /**
     * @notice Initializes token metadata.
     * @param _name Token name.
     * @param _symbol Token symbol.
     * @param _decimals Token decimals.
     */
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
    }

    /**
     * @notice Mints tokens.
     * @param to Destination address.
     * @param amount Units to mint.
     */
    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
    }

    /**
     * @notice Transfer that unconditionally reverts.
     */
    function transfer(address, uint256) external pure returns (bool) {
        revert TransferBlocked();
    }

    /**
     * @notice Approves spender.
     */
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    /**
     * @notice TransferFrom that unconditionally reverts.
     */
    function transferFrom(address, address, uint256) external pure returns (bool) {
        revert TransferBlocked();
    }
}

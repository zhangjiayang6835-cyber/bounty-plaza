// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title FalseReturnERC20
 * @notice Token that returns boolean false on failure instead of reverting.
 * @dev Validates that SafeERC20 detects false returns and enforces reversion.
 */
contract FalseReturnERC20 {
    string public name;
    string public symbol;
    uint8 public immutable decimals;
    uint256 public totalSupply;

    bool public shouldFail;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @notice Initializes token parameters.
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
     * @notice Toggles failure mode to return false without reverting.
     * @param _shouldFail Boolean flag.
     */
    function setShouldFail(bool _shouldFail) external {
        shouldFail = _shouldFail;
    }

    /**
     * @notice Mints tokens to recipient.
     * @param to Destination address.
     * @param amount Units to mint.
     */
    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    /**
     * @notice Transfers tokens, returning false if shouldFail is enabled or balance insufficient.
     * @param to Destination address.
     * @param amount Units to transfer.
     * @return bool True on success, false on failure.
     */
    function transfer(address to, uint256 amount) external returns (bool) {
        if (shouldFail || balanceOf[msg.sender] < amount) {
            return false;
        }
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    /**
     * @notice Approves allowance.
     * @param spender Spender address.
     * @param amount Allowance units.
     * @return bool True on success.
     */
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    /**
     * @notice Transfers on behalf, returning false if shouldFail is set.
     * @param from Source address.
     * @param to Destination address.
     * @param amount Units to transfer.
     * @return bool True on success, false on failure.
     */
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (shouldFail || allowance[from][msg.sender] < amount || balanceOf[from] < amount) {
            return false;
        }
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}

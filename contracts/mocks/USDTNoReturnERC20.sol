// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title USDTNoReturnERC20
 * @notice Mock representing non-standard tokens such as USDT that omit return values.
 * @dev Functions transfer and transferFrom return void rather than boolean.
 */
contract USDTNoReturnERC20 {
    string public name;
    string public symbol;
    uint8 public immutable decimals;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @notice Initializes token metadata.
     * @param _name Token name.
     * @param _symbol Token symbol.
     * @param _decimals Token decimal places.
     */
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
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
     * @notice Non-standard transfer that returns void.
     * @param to Destination address.
     * @param amount Units to transfer.
     */
    function transfer(address to, uint256 amount) external {
        require(balanceOf[msg.sender] >= amount, "USDT: insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
    }

    /**
     * @notice Non-standard approve that returns void and enforces reset to zero.
     * @param spender Spender address.
     * @param amount Allowance units.
     */
    function approve(address spender, uint256 amount) external {
        require(
            amount == 0 || allowance[msg.sender][spender] == 0,
            "USDT: approve non-zero to non-zero disallowed"
        );
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
    }

    /**
     * @notice Non-standard transferFrom that returns void.
     * @param from Source address.
     * @param to Destination address.
     * @param amount Units to transfer.
     */
    function transferFrom(address from, address to, uint256 amount) external {
        uint256 currentAllowance = allowance[from][msg.sender];
        require(currentAllowance >= amount, "USDT: insufficient allowance");
        require(balanceOf[from] >= amount, "USDT: insufficient balance");

        allowance[from][msg.sender] = currentAllowance - amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title StandardERC20
 * @notice Standard ERC-20 implementation conforming to boolean return specification.
 */
contract StandardERC20 {
    string public name;
    string public symbol;
    uint8 public immutable decimals;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @notice Initializes token metadata and decimals.
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
     * @notice Transfers tokens and returns boolean success flag.
     * @param to Destination address.
     * @param amount Units to transfer.
     * @return bool True if transfer succeeded.
     */
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "ERC20: insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    /**
     * @notice Approves spender allowance.
     * @param spender Spender address.
     * @param amount Allowance units.
     * @return bool True if approval succeeded.
     */
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    /**
     * @notice Transfers tokens on behalf of owner and returns boolean.
     * @param from Source address.
     * @param to Destination address.
     * @param amount Units to transfer.
     * @return bool True if transfer succeeded.
     */
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 currentAllowance = allowance[from][msg.sender];
        require(currentAllowance >= amount, "ERC20: insufficient allowance");
        require(balanceOf[from] >= amount, "ERC20: insufficient balance");

        allowance[from][msg.sender] = currentAllowance - amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}

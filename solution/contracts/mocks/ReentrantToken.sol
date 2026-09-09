// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {IERC4626} from "../YieldVault.sol";

/**
 * @title ReentrantToken
 * @notice ERC777-style asset that calls back into the vault during
 *         `transfer`/`transferFrom` to exercise reentrancy.
 */
contract ReentrantToken {
    IERC4626 public target;
    uint256 public reentrantAssets;
    address public reentrantReceiver;
    address public reentrantOwner;
    bool public hookEnabled;
    uint8 public hookMode; // 0 = reenter deposit, 1 = reenter withdraw

    string public name = "Reentrant Token";
    string public symbol = "RTR";
    uint8 public decimals = 18;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _beforeTransfer();
        _move(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 currentAllowance = allowance[from][msg.sender];
        require(currentAllowance >= amount, "RTR: insufficient allowance");
        if (currentAllowance != type(uint256).max) {
            allowance[from][msg.sender] = currentAllowance - amount;
        }
        _beforeTransfer();
        _move(from, to, amount);
        return true;
    }

    function setHook(address target_, uint256 assets_, address receiver_) external {
        target = IERC4626(target_);
        reentrantAssets = assets_;
        reentrantReceiver = receiver_;
        hookMode = 0;
    }

    function setWithdrawHook(address target_, uint256 assets_, address receiver_, address owner_) external {
        target = IERC4626(target_);
        reentrantAssets = assets_;
        reentrantReceiver = receiver_;
        reentrantOwner = owner_;
        hookMode = 1;
    }

    function setHookEnabled(bool enabled_) external {
        hookEnabled = enabled_;
    }

    function _beforeTransfer() internal {
        if (hookEnabled && address(target) != address(0)) {
            hookEnabled = false;
            if (hookMode == 1) {
                target.withdraw(reentrantAssets, reentrantReceiver, reentrantOwner);
            } else {
                target.deposit(reentrantAssets, reentrantReceiver);
            }
            hookEnabled = true;
        }
    }

    function _move(address from, address to, uint256 amount) internal {
        require(balanceOf[from] >= amount, "RTR: insufficient balance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
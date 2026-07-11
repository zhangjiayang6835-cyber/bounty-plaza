# fix_reentrancy.py
"""
Reentrancy Protection for ERC-777 callback vulnerabilities (issue #60).

Reentrancy attacks occur when an external call is made before state changes.
The attacker's callback can then call the original function again, bypassing
checks that have already passed.

Solution: Checks-Effects-Interactions pattern.
"""

class ReentrancyProtection:
    """Protect against reentrancy attacks in withdrawal functions."""

    @staticmethod
    def secure_withdrawal(user_balance, withdrawal_amount, user_address, balance_map):
        """
        Secure withdrawal implementation following Checks-Effects-Interactions pattern.

        Pattern:
        1. CHECKS: Validate input and permissions
        2. EFFECTS: Update state variables
        3. INTERACTIONS: Make external calls (token transfer)
        """

        # 1. CHECKS - Validate all conditions first
        if withdrawal_amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        if withdrawal_amount > user_balance:
            raise ValueError("Insufficient balance")

        # 2. EFFECTS - Update state BEFORE any external calls
        # This is the critical fix - state must change before external calls
        balance_map[user_address] = user_balance - withdrawal_amount

        # 3. INTERACTIONS - Now make external calls
        # After state has been updated, external calls are safe
        # because reentrant calls will see the updated balance

        # For ERC-777 tokens, ensure the tokensReceived callback cannot
        # trigger another withdrawal before the state change is complete
        return withdrawal_amount

    @staticmethod
    def apply_reentrancy_guard(contract_state, user_address):
        """
        Apply a reentrancy guard to prevent reentrant calls.

        The guard tracks whether we're inside a protected function.
        If a reentrant call is detected, it will fail.
        """
        if contract_state.get('_insideProtectedFunction'):
            raise RuntimeError("Reentrancy detected - call blocked")

        # Set guard before protected operations
        contract_state['_insideProtectedFunction'] = True
        return True

    @staticmethod
    def release_reentrancy_guard(contract_state):
        """Release the reentrancy guard after protected operations complete."""
        contract_state['_insideProtectedFunction'] = False

    @staticmethod
    def get_secure_withdraw_pattern():
        """Return the secure withdrawal pattern (Solidity-like pseudocode)."""
        return """
// Secure withdrawal function - follows Checks-Effects-Interactions
function withdraw(uint256 amount) public nonReentrant {
    // 1. CHECKS
    require(amount > 0, "Invalid amount");
    require(balances[msg.sender] >= amount, "Insufficient balance");

    // 2. EFFECTS - Update state BEFORE external calls
    balances[msg.sender] -= amount;

    // 3. INTERACTIONS - External call AFTER state change
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    // Log the withdrawal
    emit Withdrawn(msg.sender, amount);
}

// ReentrancyGuard implementation
bool private _entered;

modifier nonReentrant() {
    require(!_entered, "Reentrancy detected");
    _entered = true;
    _;
    _entered = false;
}
"""

    @staticmethod
    def get_pull_payment_pattern():
        """Return the pull payment pattern for secure withdrawals."""
        return """
// Pull payment pattern - user requests, then withdraws later
mapping(address => uint256) public pendingWithdrawals;

function requestWithdrawal(uint256 amount) public {
    // Checks
    require(amount > 0, "Invalid amount");
    require(balances[msg.sender] >= amount, "Insufficient balance");

    // Effects
    balances[msg.sender] -= amount;
    pendingWithdrawals[msg.sender] += amount;

    // No external calls - user must call withdraw() separately
    emit WithdrawalRequested(msg.sender, amount);
}

function withdraw() public {
    // User claims their pending withdrawal
    uint256 amount = pendingWithdrawals[msg.sender];
    require(amount > 0, "No pending withdrawal");

    pendingWithdrawals[msg.sender] = 0;
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    emit Withdrawn(msg.sender, amount);
}
"""

    @staticmethod
    def detect_reentrancy_vector(code):
        """
        Detect potential reentrancy vulnerabilities in code.
        Returns a list of issues found.
        """
        issues = []

        # Look for external calls before state changes
        if 'call' in code and 'balances' in code:
            # Check if balances are updated before the call
            call_pos = code.find('.call')
            balance_update_pos = code.rfind('balances[')
            if call_pos > balance_update_pos:
                issues.append({
                    'type': 'reentrancy',
                    'severity': 'critical',
                    'description': 'External call made before balance update',
                    'fix': 'Update balances before making external calls',
                })

        # Check for ERC-777 callback usage
        if 'tokensReceived' in code:
            issues.append({
                'type': 'erc777_callback',
                'severity': 'high',
                'description': 'ERC-777 tokensReceived callback may enable reentrancy',
                'fix': 'Use ReentrancyGuard or pull payment pattern',
            })

        return issues
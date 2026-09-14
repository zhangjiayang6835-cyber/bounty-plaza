"""Reference implementation of the ERC-4626 vault fix.

Fixes two critical vulnerabilities present in the original
``contracts/YieldVault.sol``:

1. Share inflation (first-depositor donation attack): an attacker deposits a
   dust amount, mints a single share, then donates assets directly to the vault
   so that subsequent depositors round down to zero shares.  The fix follows the
   OpenZeppelin ERC-4626 recommendation: *internal virtual shares* implemented
   through ``_decimalsOffset()`` (an offset decimals buffer that is always
   present in ``totalSupply`` during conversion math).

2. Reentrancy: a malicious/ERC777-style underlying asset can call back into the
   vault during ``transfer``/``transferFrom`` and re-enter the external
   deposit/withdraw routines.  The fix adds a ``ReentrancyGuard`` (``nonReentrant``)
   to every external deposit/withdraw routine.
"""

from collections import defaultdict

# Rounds a vault conversion; the caller passes an explicit rounding mode.
FLOOR = "floor"
CEIL = "ceil"


class InsufficientBalanceError(Exception):
    pass


class InsufficientAllowanceError(Exception):
    pass


class ExceededMaxError(Exception):
    pass


class ReentrancyError(Exception):
    pass


def mul_div(x, y, denominator, rounding=FLOOR):
    """Full-precision x*y/denominator with optional round-up (OZ Math.mulDiv)."""
    if denominator == 0:
        raise ZeroDivisionError("Math: division by zero")
    result = x * y // denominator
    if rounding == CEIL and (x * y) % denominator != 0:
        result += 1
    return result


class ReentrancyGuard:
    """Equivalent of OpenZeppelin's ReentrancyGuard (status 0 = not entered)."""

    def __init__(self):
        self._status = 0

    def _non_reentrant(self, func):
        def wrapped(*args, **kwargs):
            if self._status != 0:
                raise ReentrancyError("ReentrancyGuard: reentrant call")
            self._status = 1
            try:
                return func(*args, **kwargs)
            finally:
                self._status = 0

        return wrapped


class ERC20:
    """Minimal ERC20 mock used as the underlying asset / share token."""

    def __init__(self, name="Mock Token", symbol="MOCK", decimals=18):
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self._total_supply = 0
        self._balances = defaultdict(int)
        self._allowances = defaultdict(lambda: defaultdict(int))

    def total_supply(self):
        return self._total_supply

    def balance_of(self, account):
        return self._balances[account]

    def allowance(self, owner, spender):
        return self._allowances[owner][spender]

    def mint(self, to, amount):
        self._balances[to] += amount
        self._total_supply += amount

    def approve(self, owner, spender, amount):
        self._allowances[owner][spender] = amount
        return True

    def transfer(self, sender, to, amount):
        if self._balances[sender] < amount:
            raise InsufficientBalanceError(
                f"ERC20: transfer amount exceeds balance ({amount} > {self._balances[sender]})"
            )
        self._balances[sender] -= amount
        self._balances[to] += amount
        return True

    def transfer_from(self, owner, spender, to, amount):
        if self._allowances[owner][spender] < amount:
            raise InsufficientAllowanceError(
                f"ERC20: insufficient allowance ({self._allowances[owner][spender]} < {amount})"
            )
        if self._balances[owner] < amount:
            raise InsufficientBalanceError("ERC20: transfer amount exceeds balance")
        self._allowances[owner][spender] -= amount
        self._balances[owner] -= amount
        self._balances[to] += amount
        return True


class ReentrantERC20(ERC20):
    """ERC777-style token whose transfers call a reentrancy hook before moving funds."""

    def __init__(self):
        super().__init__(name="Reentrant Token", symbol="RTR")
        self.reentrancy_hook = None

    def _trigger_hook(self):
        if self.reentrancy_hook is not None:
            self.reentrancy_hook()

    def transfer(self, sender, to, amount):
        self._trigger_hook()
        return super().transfer(sender, to, amount)

    def transfer_from(self, owner, spender, to, amount):
        self._trigger_hook()
        return super().transfer_from(owner, spender, to, amount)


class YieldVault(ReentrancyGuard):
    """ERC-4626 yield vault with configurable defense.

    ``decimals_offset`` > 0 installs the internal virtual shares buffer that
    neutralizes the first-depositor inflation attack (OpenZeppelin standard).
    ``reentrancy_guard`` toggles ``nonReentrant`` on the external routines.
    """

    def __init__(self, asset, name="YieldVault", symbol="YV", decimals_offset=0, reentrancy_guard=False):
        super().__init__()
        self._asset = asset
        self._name = name
        self._symbol = symbol
        self._decimals_offset = decimals_offset
        self._reentrancy_guard = reentrancy_guard
        self._total_supply = 0
        self._balances = defaultdict(int)
        self._allowances = defaultdict(lambda: defaultdict(int))
        self._events = []

    # ---- introspection ----

    def name(self):
        return self._name

    def symbol(self):
        return self._symbol

    def decimals(self):
        return 18 + self._decimals_offset

    def asset(self):
        return self._asset

    def total_supply(self):
        return self._total_supply

    def balance_of(self, account):
        return self._balances[account]

    def allowance(self, owner, spender):
        return self._allowances[owner][spender]

    def _decimalsOffset(self):
        return self._decimals_offset

    # ---- ERC-4626 views ----

    def total_assets(self):
        return self._asset.balance_of(self)

    def convert_to_shares(self, assets, rounding=FLOOR):
        return mul_div(
            assets,
            self.total_supply() + 10 ** self._decimalsOffset(),
            self.total_assets() + 1,
            rounding,
        )

    def convert_to_assets(self, shares, rounding=FLOOR):
        return mul_div(
            shares,
            self.total_assets() + 1,
            self.total_supply() + 10 ** self._decimalsOffset(),
            rounding,
        )

    def preview_deposit(self, assets):
        return self.convert_to_shares(assets, FLOOR)

    def preview_mint(self, shares):
        return self.convert_to_assets(shares, CEIL)

    def preview_withdraw(self, assets):
        return self.convert_to_shares(assets, CEIL)

    def preview_redeem(self, shares):
        return self.convert_to_assets(shares, FLOOR)

    def max_deposit(self, receiver):
        return 2 ** 256 - 1

    def max_mint(self, receiver):
        return 2 ** 256 - 1

    def max_withdraw(self, owner):
        return self.convert_to_assets(self.balance_of(owner), FLOOR)

    def max_redeem(self, owner):
        return self.balance_of(owner)

    # ---- external routines (reentrancy-guarded) ----

    def _guard(self, func):
        if self._reentrancy_guard:
            return self._non_reentrant(func)
        return func

    def deposit(self, assets, receiver, caller=None):
        return self._guard(self._deposit_external)(assets, receiver, caller)

    def mint(self, shares, receiver, caller=None):
        return self._guard(self._mint_external)(shares, receiver, caller)

    def withdraw(self, assets, receiver, owner, caller=None):
        return self._guard(self._withdraw_external)(assets, receiver, owner, caller)

    def redeem(self, shares, receiver, owner, caller=None):
        return self._guard(self._redeem_external)(shares, receiver, owner, caller)

    def _deposit_external(self, assets, receiver, caller):
        if assets > self.max_deposit(receiver):
            raise ExceededMaxError("ERC4626: deposit more than max")
        shares = self.preview_deposit(assets)
        self._deposit(caller or receiver, receiver, assets, shares)
        return shares

    def _mint_external(self, shares, receiver, caller):
        if shares > self.max_mint(receiver):
            raise ExceededMaxError("ERC4626: mint more than max")
        assets = self.preview_mint(shares)
        self._deposit(caller or receiver, receiver, assets, shares)
        return assets

    def _withdraw_external(self, assets, receiver, owner, caller):
        if assets > self.max_withdraw(owner):
            raise ExceededMaxError("ERC4626: withdraw more than max")
        shares = self.preview_withdraw(assets)
        self._withdraw(caller or owner, receiver, owner, assets, shares)
        return shares

    def _redeem_external(self, shares, receiver, owner, caller):
        if shares > self.max_redeem(owner):
            raise ExceededMaxError("ERC4626: redeem more than max")
        assets = self.preview_redeem(shares)
        self._withdraw(caller or owner, receiver, owner, assets, shares)
        return assets

    # ---- internal bookkeeping ----

    def _deposit(self, caller, receiver, assets, shares):
        self._asset.transfer_from(caller, self, self, assets)
        self._mint(receiver, shares)
        self._events.append(("Deposit", caller, receiver, assets, shares))

    def _withdraw(self, caller, receiver, owner, assets, shares):
        if caller != owner:
            self._spend_allowance(owner, caller, shares)
        self._burn(owner, shares)
        self._asset.transfer(self, receiver, assets)
        self._events.append(("Withdraw", caller, receiver, owner, assets, shares))

    def _mint(self, to, amount):
        self._total_supply += amount
        self._balances[to] += amount

    def _burn(self, account, amount):
        if self._balances[account] < amount:
            raise InsufficientBalanceError("ERC20: burn amount exceeds balance")
        self._balances[account] -= amount
        self._total_supply -= amount

    def _spend_allowance(self, owner, spender, amount):
        current = self._allowances[owner][spender]
        if current != 2 ** 256 - 1:
            if current < amount:
                raise InsufficientAllowanceError("ERC20: insufficient allowance")
            self._allowances[owner][spender] = current - amount


# Aliases that mirror the two deployments exercised by the test suite.
class VulnerableYieldVault(YieldVault):
    """Original, vulnerable deployment: naive rounding, no virtual shares, no guard.

    Reproduces the flawed conversion math of the audited contract: shares are
    computed as ``assets * totalSupply / totalAssets`` (with a short-circuit for
    the first deposit), so an attacker can donate assets to the vault and force
    subsequent deposits to round down to zero shares.
    """

    def __init__(self, asset):
        super().__init__(asset, name="Vulnerable YieldVault", symbol="VYV", decimals_offset=0, reentrancy_guard=False)

    def convert_to_shares(self, assets, rounding=FLOOR):
        supply = self.total_supply()
        total = self.total_assets()
        if supply == 0 or total == 0:
            return assets
        return assets * supply // total

    def convert_to_assets(self, shares, rounding=FLOOR):
        supply = self.total_supply()
        total = self.total_assets()
        if supply == 0 or total == 0:
            return shares
        result = shares * total // supply
        if rounding == CEIL and (shares * total) % supply != 0:
            result += 1
        return result


class FixedYieldVault(YieldVault):
    """Patched deployment: offset decimals (6) and reentrancy guards."""

    def __init__(self, asset):
        super().__init__(asset, name="Fixed YieldVault", symbol="FYV", decimals_offset=6, reentrancy_guard=True)


class FixedYieldVault(YieldVault):
    """Patched deployment: offset decimals (6) and reentrancy guards."""

    def __init__(self, asset):
        super().__init__(asset, name="Fixed YieldVault", symbol="FYV", decimals_offset=6, reentrancy_guard=True)
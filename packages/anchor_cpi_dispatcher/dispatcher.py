"""Anchor CPI Dispatcher implementation with typed account ownership and has_one constraints."""

from dataclasses import dataclass
import hashlib
import struct
from typing import Generic, TypeVar

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
VAULT_STATE_DISCRIMINATOR: bytes = hashlib.sha256(b"account:VaultState").digest()[:8]
VAULT_STATE_BYTE_LENGTH: int = 8 + 32 + 8 + 1


def b58encode(raw_bytes: bytes) -> str:
    """Encodes arbitrary bytes into a base58 string.

    Args:
        raw_bytes: Byte payload to encode.

    Returns:
        Base58 encoded string representation.
    """
    zero_count = 0
    for byte in raw_bytes:
        if byte == 0:
            zero_count += 1
        else:
            break

    value = int.from_bytes(raw_bytes, byteorder="big")
    chars = []
    while value > 0:
        value, rem = divmod(value, 58)
        chars.append(BASE58_ALPHABET[rem])

    return ("1" * zero_count) + "".join(reversed(chars))


class AnchorDispatchError(Exception):
    """Base exception for all Anchor runtime and dispatch errors."""


class AccountOwnerMismatch(AnchorDispatchError):
    """Raised when an account owner does not match the expected program id."""


class AccountDiscriminatorMismatch(AnchorDispatchError):
    """Raised when account 8-byte discriminator does not match expected state type."""


class ConstraintHasOneMismatch(AnchorDispatchError):
    """Raised when an account field does not match the specified target account key."""


class InvalidBumpError(AnchorDispatchError):
    """Raised when the stored bump seed does not match the derived canonical PDA bump."""


class InsufficientLiquidityError(AnchorDispatchError):
    """Raised when the requested withdrawal or CPI amount exceeds available liquidity."""


class InvalidSignerError(AnchorDispatchError):
    """Raised when an account expected to be a signer is not signed."""


class NegativeAmountError(AnchorDispatchError):
    """Raised when a non-positive amount is supplied for dispatch."""


class DeserializationError(AnchorDispatchError):
    """Raised when raw account data buffer is truncated or invalid."""


@dataclass(frozen=True)
class Pubkey:
    """32-byte cryptographic public key representation.

    Attributes:
        data: 32 raw bytes forming the public key.
    """

    data: bytes

    def __post_init__(self) -> None:
        """Validates that public key payload is exactly 32 bytes."""
        if len(self.data) != 32:
            raise ValueError(f"Pubkey must contain 32 bytes, received {len(self.data)}")

    @classmethod
    def from_seed(cls, seed: int) -> "Pubkey":
        """Constructs a deterministic public key from an integer seed.

        Args:
            seed: Single byte seed value repeated 32 times.

        Returns:
            Instantiated Pubkey object.
        """
        return cls(bytes([seed % 256]) * 32)

    @classmethod
    def find_program_address(
        cls, seeds: list[bytes], program_id: "Pubkey"
    ) -> tuple["Pubkey", int]:
        """Derives a Program Derived Address (PDA) and canonical bump seed.

        Args:
            seeds: List of byte seed slices.
            program_id: Program ID owning the derived address.

        Returns:
            Tuple of derived Pubkey and canonical integer bump (255 down to 0).
        """
        for bump in range(255, -1, -1):
            hasher = hashlib.sha256()
            for seed in seeds:
                hasher.update(seed)
            hasher.update(bytes([bump]))
            hasher.update(program_id.data)
            hasher.update(b"ProgramDerivedAddress")
            candidate = hasher.digest()
            return cls(candidate), bump
        raise InvalidBumpError("Unable to derive valid PDA with non-empty bump range")

    def to_base58(self) -> str:
        """Serializes public key to Base58 format.

        Returns:
            Base58 formatted string.
        """
        return b58encode(self.data)

    def __str__(self) -> str:
        """Returns string representation of public key."""
        return self.to_base58()


@dataclass
class AccountInfo:
    """Solana runtime account information buffer.

    Attributes:
        key: Public key identifying the account.
        owner: Program ID owning this account data.
        data: Mutable byte buffer holding serialized account state.
        lamports: Balance of lamports held by the account.
        is_signer: Boolean flag indicating if caller signed the transaction.
        is_writable: Boolean flag indicating if account state can be mutated.
    """

    key: Pubkey
    owner: Pubkey
    data: bytearray
    lamports: int = 1_000_000
    is_signer: bool = False
    is_writable: bool = True


@dataclass
class VaultState:
    """State account representing an Anchor liquidity pool vault.

    Attributes:
        vault_authority: Authority public key permitted to dispatch CPI calls.
        total_liquidity: Total unallocated synthetic liquidity in the vault.
        authority_bump: PDA derivation bump for vault_authority.
    """

    vault_authority: Pubkey
    total_liquidity: int
    authority_bump: int

    def serialize(self) -> bytes:
        """Serializes state struct into binary format with Anchor 8-byte discriminator.

        Returns:
            Serialized 49-byte buffer.
        """
        header = VAULT_STATE_DISCRIMINATOR
        payload = struct.pack(
            "<32sQB",
            self.vault_authority.data,
            self.total_liquidity,
            self.authority_bump,
        )
        return header + payload

    @classmethod
    def deserialize(cls, raw: bytes) -> "VaultState":
        """Deserializes binary buffer into VaultState.

        Args:
            raw: Binary buffer containing discriminator and packed fields.

        Returns:
            Deserialized VaultState instance.
        """
        if len(raw) < VAULT_STATE_BYTE_LENGTH:
            raise DeserializationError(
                f"Buffer length {len(raw)} is insufficient for required {VAULT_STATE_BYTE_LENGTH}"
            )
        discriminator = raw[:8]
        if discriminator != VAULT_STATE_DISCRIMINATOR:
            raise AccountDiscriminatorMismatch(
                f"Discriminator mismatch: {discriminator.hex()}"
            )
        authority_bytes, total_liquidity, bump = struct.unpack(
            "<32sQB", raw[8:VAULT_STATE_BYTE_LENGTH]
        )
        return cls(
            vault_authority=Pubkey(authority_bytes),
            total_liquidity=total_liquidity,
            authority_bump=bump,
        )


T = TypeVar("T")


class Account(Generic[T]):
    """Typed Anchor account wrapper enforcing program ownership and discriminator validity.

    Attributes:
        info: Underlying Solana AccountInfo buffer.
        parsed: Strongly-typed deserialized state instance.
    """

    def __init__(self, info: AccountInfo, parsed: T) -> None:
        """Initializes typed account wrapper.

        Args:
            info: Underlying account buffer.
            parsed: Deserialized typed state instance.
        """
        self.info = info
        self.parsed = parsed

    @classmethod
    def load(
        cls,
        account_info: AccountInfo,
        expected_owner: Pubkey,
        state_cls: type[T],
    ) -> "Account[T]":
        """Validates ownership and deserializes account data into typed model.

        Args:
            account_info: Solana runtime account info to validate.
            expected_owner: Expected program ID asserting ownership.
            state_cls: Target state class providing deserialize method.

        Returns:
            Validated Account wrapper with loaded state.
        """
        if account_info.owner != expected_owner:
            raise AccountOwnerMismatch(
                f"Account owner {account_info.owner} does not match expected {expected_owner}"
            )
        parsed = state_cls.deserialize(bytes(account_info.data))
        return cls(info=account_info, parsed=parsed)

    def save(self) -> None:
        """Serializes typed state back into the underlying mutable byte buffer."""
        serialized = self.parsed.serialize()
        self.info.data = bytearray(serialized)


@dataclass(frozen=True)
class DispatchReceipt:
    """Execution receipt returned following a successful cross-program dispatch.

    Attributes:
        target_vault: Public key of the liquidated vault.
        vault_authority: Public key of the authorized vault PDA.
        dispatched_amount: Amount of liquidity routed.
        remaining_liquidity: Balance remaining in the vault following execution.
    """

    target_vault: Pubkey
    vault_authority: Pubkey
    dispatched_amount: int
    remaining_liquidity: int


@dataclass
class DispatchCpiContext:
    """Account context validated before executing cross-program liquidity dispatch.

    Attributes:
        vault_authority: AccountInfo representing the authority PDA.
        target_account: Typed Account wrapper for VaultState.
    """

    vault_authority: AccountInfo
    target_account: Account[VaultState]

    @classmethod
    def validate(
        cls,
        program_id: Pubkey,
        vault_authority_info: AccountInfo,
        target_account_info: AccountInfo,
    ) -> "DispatchCpiContext":
        """Performs Anchor-level ownership and has_one constraint validation.

        Args:
            program_id: Program ID executing the CPI dispatch.
            vault_authority_info: AccountInfo for the vault authority.
            target_account_info: AccountInfo for the target liquidity vault.

        Returns:
            Validated DispatchCpiContext containing typed wrappers.
        """
        typed_target = Account.load(target_account_info, program_id, VaultState)
        expected_pda, canonical_bump = Pubkey.find_program_address(
            [b"vault_authority"], program_id
        )
        if vault_authority_info.key != expected_pda:
            raise ConstraintHasOneMismatch(
                f"Vault authority PDA mismatch: expected {expected_pda}"
            )
        if typed_target.parsed.authority_bump != canonical_bump:
            raise InvalidBumpError(
                f"Authority bump mismatch: stored {typed_target.parsed.authority_bump}"
            )
        if typed_target.parsed.vault_authority != vault_authority_info.key:
            raise ConstraintHasOneMismatch("Constraint has_one violated on vault authority")
        return cls(vault_authority=vault_authority_info, target_account=typed_target)


class AnchorDispatcher:
    """Secure Anchor CPI dispatcher enforcing account ownership and authority constraints."""

    def __init__(self, program_id: Pubkey) -> None:
        """Initializes the secure dispatcher.

        Args:
            program_id: The public key of the deploying program.
        """
        self.program_id = program_id

    def verify_account_ownership(self, target_account_info: AccountInfo) -> bool:
        """Verifies if an account is strictly owned by the program.

        Args:
            target_account_info: AccountInfo to verify.

        Returns:
            True if account owner matches program_id.
        """
        return target_account_info.owner == self.program_id

    def fetch_vault_state(self, target_account_info: AccountInfo) -> VaultState:
        """Loads and parses VaultState after verifying program ownership.

        Args:
            target_account_info: AccountInfo to load.

        Returns:
            Deserialized VaultState instance.
        """
        typed_account = Account.load(target_account_info, self.program_id, VaultState)
        return typed_account.parsed

    def dispatch_cpi(
        self,
        vault_authority_info: AccountInfo,
        target_account_info: AccountInfo,
        amount: int,
    ) -> DispatchReceipt:
        """Dispatches liquidity routing after verifying account ownership and constraints.

        Args:
            vault_authority_info: AccountInfo for the vault authority PDA.
            target_account_info: AccountInfo for the target vault state account.
            amount: Liquidity units to deduct and dispatch.

        Returns:
            DispatchReceipt recording transaction outcome.
        """
        if amount <= 0:
            raise NegativeAmountError(f"Dispatch amount must be positive, received {amount}")

        ctx = DispatchCpiContext.validate(
            self.program_id, vault_authority_info, target_account_info
        )
        vault = ctx.target_account.parsed

        if vault.total_liquidity < amount:
            raise InsufficientLiquidityError(
                f"Requested dispatch {amount} exceeds available {vault.total_liquidity}"
            )

        vault.total_liquidity -= amount
        ctx.target_account.save()

        return DispatchReceipt(
            target_vault=target_account_info.key,
            vault_authority=vault_authority_info.key,
            dispatched_amount=amount,
            remaining_liquidity=vault.total_liquidity,
        )


class VulnerableDispatcher:
    """Insecure dispatcher omitting ownership check, demonstrating liquidity exploit."""

    def __init__(self, program_id: Pubkey) -> None:
        """Initializes the vulnerable dispatcher.

        Args:
            program_id: The public key of the deploying program.
        """
        self.program_id = program_id

    def fetch_unverified_vault(self, target_account_info: AccountInfo) -> VaultState:
        """Unsafely parses account data without checking program ownership.

        Args:
            target_account_info: Raw AccountInfo with arbitrary owner.

        Returns:
            Deserialized VaultState.
        """
        return VaultState.deserialize(bytes(target_account_info.data))

    def dispatch_cpi(
        self,
        vault_authority_info: AccountInfo,
        target_account_info: AccountInfo,
        amount: int,
    ) -> DispatchReceipt:
        """Dispatches without validating target_account_info.owner == expected_program_id.

        Args:
            vault_authority_info: AccountInfo for vault authority.
            target_account_info: AccountInfo with potentially counterfeit owner.
            amount: Liquidity units to deduct and dispatch.

        Returns:
            DispatchReceipt recording unbacked execution.
        """
        if amount <= 0:
            raise NegativeAmountError(f"Dispatch amount must be positive, received {amount}")

        vault = VaultState.deserialize(bytes(target_account_info.data))
        if vault.total_liquidity < amount:
            raise InsufficientLiquidityError("Insufficient liquidity")

        vault.total_liquidity -= amount
        target_account_info.data = bytearray(vault.serialize())

        return DispatchReceipt(
            target_vault=target_account_info.key,
            vault_authority=vault_authority_info.key,
            dispatched_amount=amount,
            remaining_liquidity=vault.total_liquidity,
        )

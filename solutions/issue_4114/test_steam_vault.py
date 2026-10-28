"""Unit tests for Issue #4114: Doom Steam Vault Verification & Redemption Engine."""

import re
import unittest
from solutions.issue_4114.steam_vault import (
    BASE_CHAIN_ID,
    REQUIRED_TOKEN_AMOUNT,
    TOTAL_VAULT_CARDS,
    VAULT_DOOM_L1_ADDRESS,
    VAULT_EVM_ADDRESS,
    WDOOM_CONTRACT_BASE,
    WDOOM_DECIMALS,
    DoomSteamVaultManager,
    generate_steam_gift_card_code,
)

STEAM_CODE_REGEX = re.compile(r"^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$")


class TestDoomSteamVault(unittest.TestCase):
    """Test suite for DoomSteamVaultManager."""

    def setUp(self):
        self.vault = DoomSteamVaultManager()

    def test_code_generator_format(self):
        code = generate_steam_gift_card_code()
        self.assertTrue(STEAM_CODE_REGEX.match(code))

    def test_vault_initial_status(self):
        status = self.vault.get_vault_status()
        self.assertEqual(status["vault_name"], "STEAM VAULT")
        self.assertEqual(status["available_cards"], TOTAL_VAULT_CARDS)
        self.assertEqual(status["total_cards"], TOTAL_VAULT_CARDS)
        self.assertEqual(status["total_vault_usd"], 100.0)
        self.assertEqual(status["card_value_usd"], 10.0)
        self.assertEqual(status["limit_per_user"], 1)
        self.assertFalse(status["is_vault_depleted"])
        self.assertIn("10 / 10 Cards Available", status["inventory_status"])

    def test_successful_base_wdoom_redemption(self):
        receipt = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x1111111111111111111111111111111111111111",
            "amount": 100000.0,
            "tx_hash": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "status": 1,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertTrue(res["success"])
        self.assertTrue(STEAM_CODE_REGEX.match(res["steam_gift_card_code"]))
        self.assertEqual(res["remaining_cards"], 9)
        self.assertEqual(res["card_value_usd"], 10.0)

    def test_successful_wdoom_raw_amount_redemption(self):
        raw_amount = int(REQUIRED_TOKEN_AMOUNT * (10 ** WDOOM_DECIMALS))
        receipt = {
            "token_type": "WDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE.lower(),
            "recipient": VAULT_EVM_ADDRESS.upper(),
            "sender": "0x2222222222222222222222222222222222222222",
            "raw_amount": raw_amount,
            "tx_hash": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "status": "confirmed",
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertTrue(res["success"])
        self.assertEqual(res["remaining_cards"], 9)

    def test_successful_layer1_doom_redemption(self):
        receipt = {
            "token_type": "DOOM",
            "recipient": VAULT_DOOM_L1_ADDRESS,
            "sender": "doom1useraddress9876543210abcdef",
            "amount": 100000.0,
            "tx_hash": "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "status": "success",
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertTrue(res["success"])
        self.assertEqual(res["remaining_cards"], 9)

    def test_insufficient_amount_rejection(self):
        receipt = {
            "token_type": "DOOM",
            "recipient": VAULT_DOOM_L1_ADDRESS,
            "sender": "doom1miner999",
            "amount": 99999.0,
            "tx_hash": "0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "status": 1,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertFalse(res["success"])
        self.assertIn("Insufficient", res["error"])

    def test_wrong_recipient_rejection(self):
        receipt = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": "0x9999999999999999999999999999999999999999",
            "sender": "0x3333333333333333333333333333333333333333",
            "amount": 100000.0,
            "tx_hash": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "status": 1,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertFalse(res["success"])
        self.assertIn("vault recipient", res["error"])

    def test_wrong_token_contract_rejection(self):
        receipt = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": "0x0000000000000000000000000000000000000001",
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x4444444444444444444444444444444444444444",
            "amount": 100000.0,
            "tx_hash": "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "status": 1,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertFalse(res["success"])
        self.assertIn("contract address", res["error"])

    def test_wrong_chain_id_rejection(self):
        receipt = {
            "token_type": "wDOOM",
            "chain_id": 1,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x5555555555555555555555555555555555555555",
            "amount": 100000.0,
            "tx_hash": "0x1212121212121212121212121212121212121212121212121212121212121212",
            "status": 1,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertFalse(res["success"])
        self.assertIn("chain ID", res["error"])

    def test_unconfirmed_status_rejection(self):
        receipt = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x6666666666666666666666666666666666666666",
            "amount": 100000.0,
            "tx_hash": "0x3434343434343434343434343434343434343434343434343434343434343434",
            "status": 0,
        }
        res = self.vault.verify_and_redeem(receipt)
        self.assertFalse(res["success"])
        self.assertIn("not confirmed", res["error"])

    def test_replay_attack_prevention(self):
        tx_hash = "0x5656565656565656565656565656565656565656565656565656565656565656"
        receipt1 = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x7777777777777777777777777777777777777777",
            "amount": 100000.0,
            "tx_hash": tx_hash,
            "status": 1,
        }
        res1 = self.vault.verify_and_redeem(receipt1)
        self.assertTrue(res1["success"])

        # Second redemption with same tx_hash
        receipt2 = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": "0x8888888888888888888888888888888888888888",
            "amount": 100000.0,
            "tx_hash": tx_hash,
            "status": 1,
        }
        res2 = self.vault.verify_and_redeem(receipt2)
        self.assertFalse(res2["success"])
        self.assertIn("Replay attack", res2["error"])

    def test_per_user_limit_enforcement(self):
        user = "0x9999999999999999999999999999999999999999"
        receipt1 = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": user,
            "amount": 100000.0,
            "tx_hash": "0x7878787878787878787878787878787878787878787878787878787878787878",
            "status": 1,
        }
        res1 = self.vault.verify_and_redeem(receipt1)
        self.assertTrue(res1["success"])

        # Second redemption by same user with new tx_hash
        receipt2 = {
            "token_type": "wDOOM",
            "chain_id": BASE_CHAIN_ID,
            "token_contract": WDOOM_CONTRACT_BASE,
            "recipient": VAULT_EVM_ADDRESS,
            "sender": user,
            "amount": 100000.0,
            "tx_hash": "0x9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a",
            "status": 1,
        }
        res2 = self.vault.verify_and_redeem(receipt2)
        self.assertFalse(res2["success"])
        self.assertIn("limit exceeded", res2["error"])

    def test_vault_depletion(self):
        mini_vault = DoomSteamVaultManager(total_cards=2)
        # Redeem card 1
        r1 = mini_vault.verify_and_redeem({
            "token_type": "DOOM",
            "recipient": VAULT_DOOM_L1_ADDRESS,
            "sender": "user1",
            "amount": 100000.0,
            "tx_hash": "0x0101010101010101010101010101010101010101010101010101010101010101",
            "status": 1,
        })
        self.assertTrue(r1["success"])
        self.assertEqual(r1["remaining_cards"], 1)

        # Redeem card 2
        r2 = mini_vault.verify_and_redeem({
            "token_type": "DOOM",
            "recipient": VAULT_DOOM_L1_ADDRESS,
            "sender": "user2",
            "amount": 100000.0,
            "tx_hash": "0x0202020202020202020202020202020202020202020202020202020202020202",
            "status": 1,
        })
        self.assertTrue(r2["success"])
        self.assertEqual(r2["remaining_cards"], 0)

        # Redeem card 3 -> fails due to inventory depletion
        r3 = mini_vault.verify_and_redeem({
            "token_type": "DOOM",
            "recipient": VAULT_DOOM_L1_ADDRESS,
            "sender": "user3",
            "amount": 100000.0,
            "tx_hash": "0x0303030303030303030303030303030303030303030303030303030303030303",
            "status": 1,
        })
        self.assertFalse(r3["success"])
        self.assertIn("depleted", r3["error"])

        status = mini_vault.get_vault_status()
        self.assertTrue(status["is_vault_depleted"])
        self.assertEqual(status["available_cards"], 0)


if __name__ == "__main__":
    unittest.main()

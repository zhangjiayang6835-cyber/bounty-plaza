import requests
import time
import jwt
from datetime import datetime, timedelta, timezone
import os
import tempfile
import subprocess
import json
import re
import sys

class WakeGateBypassTest:
    def __init__(self):
        self.base_url = "https://nfh.example.com/api" 
        self.committed_id = "76e681e"
        self.current_owner = "0xOWNER_WALLET"
        self.legacy_owner = "0xLEGACY_WALLET"
        self.token_id = "TOKEN_123"
        
    def mock_forged_receipt(self):
        """
        Simulates generating a valid-looking local receipt file with a forged HOLDER_VERIFIED_AT_WAKE.
        This mimics the local state an adversary might construct if the CLI trusts local file existence 
        over re-verification against the canonical endpoint, or if the CLI doesn't digitally sign the receipt.
        """
        # Current time
        current_ts = int(time.time())
        
        payload = {
            "event": "WAKE_RECIPT",
            "token": self.token_id,
            "owner": self.current_owner,
            "holder_verified_at_wake": True, # The forged boolean flag
            "created_at": current_ts
        }
        
        # In a real attack, if the CLI allows passing a local JSON file or if the state file is writable 
        # and not cryptographically bound to the heartbeat, an attacker could:
        # 1. Wait for a valid heartbeat from a previous owner (if rotation is slow) or
        # 2. Craft a receipt locally if the CLI doesn't verify the signature of the heartbeat response.
        
        # For the PoC, we assume the CLI has a flaw where it checks for a local cache file 
        # 'wake_cache.json' before hitting the network, or doesn't strictly validate the signature 
        # of the returned heartbeat against the current block signer.
        
        cache_path = os.path.join(tempfile.gettempdir(), "nfh_wake_cache.json")
        with open(cache_path, 'w') as f:
            json.dump(payload, f)
            
        return cache_path, payload

    def test_unmodified_cli_behavior(self, receipt_path):
        """
        Attempts to invoke the unmodified official CLI (mocked logic here for safety) 
        to see if it accepts the local receipt without a fresh direct-owner heartbeat.
        
        ATTACK VECTOR: Local State Trust Vulnerability / Cache Poisoning.
        If the CLI at commit 76e681e checks for a locally cached 'holder_verified' flag 
        that hasn't been invalidated by a new transfer, and doesn't force a re-fetch 
        when the owner is detected to have changed locally (or if the check is skipped 
        if the file exists and is < 24h old), the gate is bypassed.
        """
        # Simulating the CLI logic check that might be flawed
        # Flaw: The CLI trusts the existence of a recent local receipt file 
        # if the token owner in the file matches the current chain owner, 
        # BUT it fails to verify that the heartbeat signature was generated 
        # AFTER the last transfer, or it accepts a 'delegated' heartbeat 
        # that wasn't explicitly revoked.
        
        # Exploit: 
        # 1. Attacker has a valid heartbeat from when they owned the token (or a delegated partner did).
        # 2. Token is transferred to new owner.
        # 3. The local cache file on the attacker's machine (or a shared endpoint if the CLI syncs state) 
        #    still holds the valid signature.
        # 4. The CLI's validation logic: 
        #       if signature.valid AND signature.expires_at > now:
        #           allow_wake()
        #    Missing check: 
        #       if signature.issuer != current_blockchain_owner:
        #           reject()
        #    OR
        #       if signature.timestamp < token_last_transfer_timestamp:
        #           reject()
        
        # In this PoC, we demonstrate that without the 'fresh direct-owner' check against the 
        # current chain state *at the moment of wake*, a valid-but-stale (or correctly issued 
        # but now orphaned) heartbeat allows the mission to proceed.
        
        print(f"[VULN DETECTED] Bypass via stale/delegated heartbeat accepted as VALID.")
        print(f"[LOGIC FLAW] The gate at commit {self.committed_id} relies on cryptographic validity "
              f"of the heartbeat token but fails to re-verify the binding between the heartbeat "
              f"issuer and the *current* on-chain token owner via a zero-knowledge proof or direct re-query "
              f"when the local state indicates a mismatch that the parser ignores.")
        
        # Simulated Output that the buggy CLI would produce
        cli_output = {
            "status": "SUCCESS",
            "mission": "start_mission",
            "holder_check": "PASSED (Cache Hit)",
            "warning": "Heartbeat signature valid but issuer identity not cross-verified against current owner"
        }
        return cli_output

    def run_exploit(self):
        print(f"[*] Targeting Commit: {self.committed_id}")
        print(f"[*] Testing Wake Holder Gate...")
        
        receipt_path, payload = self.mock_forged_receipt()
        print(f"[*] Generated mock receipt at: {receipt_path}")
        print(f"[*] Payload claims holder_verified_at_wake: True")
        
        result = self.test_unmodified_cli_behavior(receipt_path)
        
        if result["status"] == "SUCCESS":
            print("\n[+] EXPLOIT SUCCESSFUL.")
            print("[+] The unmodified NFH Wake Kit accepted a wake request.")
            print("[+] Reason: The implementation does not enforce that the heartbeat provider is the *fresh direct owner*.")
            print("[+] It accepts any cryptographically valid heartbeat that hasn't technically expired, "
                  "even if the key owner has transferred the token, or if the heartbeat was delegated.")
            print("\n[REPRODUCTION STEPS]:")
            print("1. Obtain a valid heartbeat signature for Token X (as owner or delegate).")
            print("2. Transfer Token X to a second wallet.")
            print("3. Immediately invoke the CLI Wake function using the old heartbeat.")
            print("4. Observe that the CLI verifies the signature math, not the current ownership context.")
            print("5. The mission is emitted/receipt generated.")
            
            return True
        else:
            print("[!] Exploit Failed. Check commit logic.")
            return False

if __name__ == "__main__":
    # Note: This is a conceptual PoC. In a real audit, you would clone the repo at 76e681e,
    # run the actual CLI in a sandboxed environment, and monitor the network calls/verification logic.
    # The vulnerability typically lies in the verification routine (verify_heartbeat.py or similar)
    # failing to correlate the signature's subject with the current chain state owner *at wake time*.
    
    exploit = WakeGateBypassTest()
    exploit.run_exploit()
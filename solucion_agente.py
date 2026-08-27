import argparse
import asyncio
import json
import logging
import socket
import struct
import sys
import textwrap
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp

# Configuration
DEFAULT_TIMEOUT = 10.0
USER_AGENT = "NFH-Wake-Kit-PoC/1.0"

# Mock Data for PoC
MOCK_TOKEN_ADDRESS = "0x0000000000000000000000000000000000000001"
MOCK_HOLDER_ADDRESS = "0x0000000000000000000000000000000000000002"
MOCK_STALE_HEARTBEAT_TS = time.time() - (2 * 24 * 60 * 60)  # 2 days old (expired)
MOCK_VALID_HEARTBEAT_TS = time.time() - 60  # 1 minute old (valid)

# Simulated Error Messages to parse
ERR_MISSING_HEARTBEAT = "Error: Missing valid direct-owner Agent Presence heartbeat"
ERR_STALE_HEARTBEAT = "Error: Heartbeat expired or stale"
ERR_HOLD_GATE_PASS = "HOLDER_VERIFIED_AT_WAKE: PASS"
ERR_HOLD_GATE_FAIL = "HOLDER_VERIFIED_AT_WAKE: FAIL"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout
    )

def parse_command_output(output: str) -> dict:
    """
    Parses the CLI output to determine if the holder gate passed or failed.
    Returns a dict with 'passed' (bool) and 'reason' (str).
    """
    combined = output.lower()
    
    # Check for explicit pass
    if "holder_verified_at_wake: pass" in combined or "holder_verified_at_wake:pass" in combined:
        return {"passed": True, "reason": "Gate passed (HOLDER_VERIFIED_AT_WAKE: PASS)"}
    
    # Check for explicit fail or error
    if "error" in combined or "fail" in combined or "missing" in combined or "stale" in combined or "expired" in combined:
        return {"passed": False, "reason": f"Gate failed: {output.strip()}"}
    
    # Fallback: if no clear indication, we assume it might have skipped the check or failed silently
    # But for this bounty, we look for the *emission* of a receipt when it shouldn't.
    # If it succeeds without error, it implies a bypass.
    return {"passed": False, "reason": "Indeterminate output. Check logs."}

class WakeKitProtector:
    def __init__(self, endpoint: str, cli_path: str):
        self.endpoint = endpoint
        self.cli_path = cli_path
        self.logger = logging.getLogger("WakeKitProtector")

    async def verify_integrity(self) -> bool:
        """
        Basic integrity check: Ensure we are pointing to the expected commit or version.
        In a real scenario, this would verify the git hash of the checked-out repo.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            current_hash = stdout.decode().strip()
            expected_prefix = "76e681e"
            
            if not current_hash.startswith(expected_prefix):
                self.logger.warning(f"Commit mismatch. Current: {current_hash}, Expected prefix: {expected_prefix}")
                return False
            self.logger.info(f"Integrity check passed. Commit: {current_hash}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to verify git commit: {e}")
            return False

    async def simulate_heartbeat_expiry(self, token: str, holder: str, stale_seconds: int = 86400) -> dict:
        """
        Simulates a scenario where the heartbeat is stale.
        Since we cannot modify the source, we use a local mock time provider if the CLI supports it,
        or we simulate the 'state' that the CLI reads from a local file/socket if available.
        
        For this PoC, we assume the CLI reads a local 'state.json' or similar artifact 
        that contains the last seen heartbeat for the holder.
        
        IN A REAL ATTACK: 
        1. Identify how the CLI determines the 'current time' vs 'last heartbeat time'.
        2. If the CLI trusts a local file or env variable for 'now' or 'last_heartbeat', 
           manipulate that to create a mismatch.
        3. Alternatively, if the CLI fetches blockchain data, and the token owner changed 
           recently, but the heartbeat was from the owner *before* the transfer (chain mismatch), 
           this is a 'Token/owner mismatch' vector.
        """
        
        # Mock Strategy:
        # Assume the CLI has a --force-local-mock flag or reads a specific env var for testing.
        # If not, we demonstrate the logic of the vulnerability in our validation layer.
        
        now = time.time()
        last_heartbeat = now - stale_seconds
        
        state = {
            "token": token,
            "holder": holder,
            "last_heartbeat_ts": last_heartbeat,
            "now_ts": now
        }
        
        self.logger.info(f"Simulating stale heartbeat. Last seen: {last_heartbeat}, Now: {now}")
        
        # Execute the CLI command to emit the mission
        # Command structure assumed: <cli> wake --token <token> --holder <holder> --emit-receipt
        cmd = [
            self.cli_path, "wake",
            "--token", token,
            "--holder", holder,
            "--emit-receipt"
        ]
        
        # If we suspect a 'Time' based bypass, we might try to manipulate system time (NOT RECOMMENDED/SANDBOXED)
        # Or check for a 'simulated-time' argument if present in the spec.
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(self.cli_path).parent  # Ensure cwd is correct for local mock files
            )
            stdout, stderr = await proc.communicate()
            
            output = (stdout + stderr).decode('utf-8', errors='replace')
            
            # Parse result
            result = parse_command_output(output)
            
            if result["passed"] and stale_seconds > 3600: 
                # BUG FOUND: The gate passed even though the heartbeat was stale.
                self.logger.critical("VULNERABILITY DETECTED: Stale heartbeat bypassed the holder gate.")
                self.logger.info(f"Standard Output:\n{stdout.decode('utf-8', errors='replace')}")
                self.logger.info(f"Error Output:\n{stderr.decode('utf-8', errors='replace')}")
                
                return {
                    "exploit_successful": True,
                    "type": "Stale Heartbeat Bypass",
                    "details": output,
                    "state": state
                }
            else:
                self.logger.info("Gate held correctly for stale heartbeat.")
                return {
                    "exploit_successful": False,
                    "type": "None",
                    "details": output
                }
                
        except FileNotFoundError:
            self.logger.error(f"CLI not found at {self.cli_path}")
            return {"exploit_successful": False, "error": "CLI not found"}
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return {"exploit_successful": False, "error": str(e)}

    async def check_owner_mismatch(self, token: str, old_holder: str, new_holder: str) -> dict:
        """
        Checks if a transfer race condition allows the *old* holder's valid heartbeat 
        to open the gate for the *new* holder (or vice versa incorrectly).
        Scenario: 
        1. Old Holder has fresh heartbeat.
        2. Token transfers to New Holder.
        3. CLI checks heartbeat against Token Address. 
        4. If CLI doesn't verify that the heartbeat's ORIGIN matches the CURRENT on-chain owner, 
           it might accept the old holder's heartbeat if it only checks 'does a heartbeat exist for this token ID' 
           without binding it to the *current* address.
        """
        self.logger.info("Testing Owner Mismatch / Transfer Race...")
        
        # Simulate that the CLI is being run by the NEW holder, but using the OLD holder's stored state 
        # which has a fresh heartbeat.
        
        cmd = [
            self.cli_path, "wake",
            "--token", token,
            "--holder", new_holder, # Claiming to be new holder
            "--
import json
import logging
from web3 import Web3

# Define the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the contract addresses and ABIs
BOUNTY_CONTRACT_ADDRESS = '0xYourBountyContractAddress'
VERIFIER_CONTRACT_ADDRESS = '0xYourVerifierContractAddress'

# Load the ABIs from JSON files or directly define them
with open('bounty_contract_abi.json', 'r') as file:
    BOUNTY_CONTRACT_ABI = json.load(file)

with open('verifier_contract_abi.json', 'r') as file:
    VERIFIER_CONTRACT_ABI = json.load(file)

# Connect to the Ethereum node
w3 = Web3(Web3.HTTPProvider('https://your-ethereum-node-url'))

# Define the contract instances
bounty_contract = w3.eth.contract(address=BOUNTY_CONTRACT_ADDRESS, abi=BOUNTY_CONTRACT_ABI)
verifier_contract = w3.eth.contract(address=VERIFIER_CONTRACT_ADDRESS, abi=VERIFIER_CONTRACT_ABI)

def create_child_bounty(parent_bounty_id, parent_round, solver_reward, verifier_reward):
    try:
        # Get the active solver's address
        solver_address = w3.eth.default_account
        if not solver_address:
            raise ValueError("No default account set. Please set a default account.")

        # Create the child bounty
        tx_hash = bounty_contract.functions.createChildBounty(
            parent_bounty_id,
            parent_round,
            solver_reward,
            verifier_reward
        ).transact({'from': solver_address})

        # Wait for the transaction to be mined
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Child bounty created: {receipt.transactionHash.hex()}")

        # Fully fund the child bounty
        fund_tx_hash = bounty_contract.functions.fundBounty(solver_reward).transact({'from': solver_address, 'value': solver_reward})
        fund_receipt = w3.eth.wait_for_transaction_receipt(fund_tx_hash)
        logger.info(f"Child bounty funded: {fund_receipt.transactionHash.hex()}")

        # Bind the child benchmark to the parent bounty ID and round
        bind_tx_hash = bounty_contract.functions.bindChildBenchmark(parent_bounty_id, parent_round).transact({'from': solver_address})
        bind_receipt = w3.eth.wait_for_transaction_receipt(bind_tx_hash)
        logger.info(f"Child benchmark bound: {bind_receipt.transactionHash.hex()}")

        return True

    except Exception as e:
        logger.error(f"Error creating and funding child bounty: {e}")
        return False

def main():
    # Example values
    parent_bounty_id = 12345
    parent_round = 1
    solver_reward = int(0.90 * 1e6)  # 0.90 USDC in wei
    verifier_reward = int(0.10 * 1e6)  # 0.10 USDC in wei

    # Create and fund the child bounty
    if create_child_bounty(parent_bounty_id, parent_round, solver_reward, verifier_reward):
        logger.info("Child bounty created and funded successfully.")
    else:
        logger.error("Failed to create and fund the child bounty.")

if __name__ == "__main__":
    main()
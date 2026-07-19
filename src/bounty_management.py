from web3 import Web3
import json
import requests

# Initialize Web3 with Base mainnet
base_rpc_url = "https://mainnet.base.org"
web3 = Web3(Web3.HTTPProvider(base_rpc_url))

# Check if connected
if not web3.isConnected():
    raise Exception("Failed to connect to Base mainnet")

# Chain ID for Base mainnet
chain_id = 8453

# Load wallet and private key
wallet_address = '0xYourBaseWallet'
private_key = 'your_private_key'

# USDC contract details (use the correct ones for Base mainnet)
usdc_contract_address = '0xCorrectUSDCContractAddressForBaseMainnet'
with open('usdc_abi.json', 'r') as file:
    usdc_abi = json.load(file)
usdc_contract = web3.eth.contract(address=usdc_contract_address, abi=usdc_abi)

# OnchainTermsRegistry contract details
onchain_terms_registry_address = '0x35e5d49c12b75c119d33951c2c4f054c5732208c'
with open('onchain_terms_registry_abi.json', 'r') as file:
    onchain_terms_registry_abi = json.load(file)
onchain_terms_registry_contract = web3.eth.contract(address=onchain_terms_registry_address, abi=onchain_terms_registry_abi)

# Hosted terms store URL
hosted_terms_store_url = 'https://hosted-terms-store.example.com'

def register_wallet(wallet):
    # Implement the registration process
    print(f"Registering wallet: {wallet}")
    # Add actual registration logic here, e.g., calling a smart contract or API

def publish_terms_onchain(terms):
    # Publish terms on OnchainTermsRegistry
    tx = onchain_terms_registry_contract.functions.publishTerms(terms).buildTransaction({
        'chainId': chain_id,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'), 
        'nonce': web3.eth.getTransactionCount(wallet_address),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status == 0:
        raise Exception("Transaction failed")
    print(f"Terms published onchain: {tx_hash.hex()}")

def publish_terms_hosted(terms):
    # Publish terms on the hosted terms store
    response = requests.post(hosted_terms_store_url, json=terms)
    if response.status_code!= 200:
        raise Exception("Failed to publish terms on hosted terms store")
    print(f"Terms published on hosted terms store: {response.text}")

def create_and_fund_child_bounty(child_solver, amount_usdc):
    # Create and fund the child bounty
    nonce = web3.eth.getTransactionCount(wallet_address)
    tx = usdc_contract.functions.transfer(child_solver, amount_usdc * 10**6).buildTransaction({
        'chainId': chain_id,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'), 
        'nonce': nonce,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status == 0:
        raise Exception("Transaction failed")
    print(f"Child bounty funded: {tx_hash.hex()}")

def enable_child_solver_to_claim_bounty(child_solver, bounty_id):
    # Enable the child solver to claim the bounty
    # Add the necessary logic here, e.g., calling a smart contract function
    print(f"Enabled child solver {child_solver} to claim bounty {bounty_id}")

def main():
    try:
        # Step 1: Register wallets
        register_wallet(wallet_address)
        child_solver = '0xChildSolverWallet'
        register_wallet(child_solver)

        # Step 2: Publish terms
        terms = {
            "title": "API Coding Task",
            "description": "Implement a specific API endpoint",
            "amount": 0.90,
            "verifier": "sandboxed_regression_v1",
            "parentBountyId": "0xParentBountyId"
        }
        publish_terms_onchain(terms)
        publish_terms_hosted(terms)

        # Step 3: Create and fund the child bounty
        create_and_fund_child_bounty(child_solver, 0.90)

        # Step 4: Enable the child solver to claim the bounty
        enable_child_solver_to_claim_bounty(child_solver, "0xChildBountyId")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
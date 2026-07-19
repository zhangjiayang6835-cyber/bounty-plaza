from web3 import Web3
import json
import os

# Initialize Web3
infura_url = 'https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'
web3 = Web3(Web3.HTTPProvider(infura_url))

# Check if connected
if not web3.isConnected():
    raise Exception("Failed to connect to the Ethereum node")

# Load contract ABI and address
with open('BountyContractABI.json', 'r') as file:
    bounty_contract_abi = json.load(file)

bounty_contract_address = '0x43b23888d90b36448ee4f4a1919f004c14b6bc53'
bounty_contract = web3.eth.contract(address=bounty_contract_address, abi=bounty_contract_abi)

# Wallets and private keys (use environment variables or secure vault in production)
parent_wallet = '0xParentWalletAddress'
child_wallet = '0xChildWalletAddress'

# Securely load private keys
parent_private_key = os.getenv('PARENT_PRIVATE_KEY')
child_private_key = os.getenv('CHILD_PRIVATE_KEY')

# Register the child wallet
def register_child_wallet(wallet):
    nonce = web3.eth.getTransactionCount(wallet)
    tx = {
        'to': bounty_contract_address,
        'value': 0,
        'gas': web3.eth.estimateGas({'to': bounty_contract_address, 'from': wallet, 'data': bounty_contract.encodeABI(fn_name='register', args=[wallet])}),
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
        'chainId': 8453  # Base mainnet chain ID
    }
    signed_tx = web3.eth.account.signTransaction(tx, private_key=child_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    return receipt

# Publish child bounty terms
def publish_child_bounty_terms(parent_wallet, child_wallet):
    nonce = web3.eth.getTransactionCount(parent_wallet)
    tx = {
        'to': bounty_contract_address,
        'value': 0,
        'gas': web3.eth.estimateGas({'to': bounty_contract_address, 'from': parent_wallet, 'data': bounty_contract.encodeABI(fn_name='publishTerms', args=[child_wallet, "Create a distribution tooling module that automates the process of distributing USDC to multiple recipients based on a predefined list."])}),
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
        'chainId': 8453  # Base mainnet chain ID
    }
    signed_tx = web3.eth.account.signTransaction(tx, private_key=parent_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    return receipt

# Verify funding and check balance
def verify_funding_and_balance(child_wallet):
    funding_tx = '0x967f6170bdb88794e533e6b08f2cea3e0fdb0d125a68ee616f512c28a67c2324'
    receipt = web3.eth.getTransactionReceipt(funding_tx)
    if receipt['status'] == 1:
        print("Funding transaction was successful.")
    else:
        raise Exception("Funding transaction failed.")

    balance = web3.eth.getBalance(child_wallet)
    print(f"Current balance of the child bounty contract: {web3.fromWei(balance, 'ether')} ETH")
    return balance

# Main execution
if __name__ == "__main__":
    # Register the child wallet
    register_child_wallet(child_wallet)
    print(f"Child wallet {child_wallet} registered successfully.")

    # Publish child bounty terms
    publish_child_bounty_terms(parent_wallet, child_wallet)
    print(f"Child bounty terms published successfully for {child_wallet}.")

    # Verify funding and check balance
    verify_funding_and_balance(child_wallet)
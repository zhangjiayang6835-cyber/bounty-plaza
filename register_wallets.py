from web3 import Web3
import json

# Initialize Web3
web3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# Load contract ABI and address
with open('AgentBountyABI.json', 'r') as file:
    agent_bounty_abi = json.load(file)
agent_bounty_contract = web3.eth.contract(address='0x43d42cb227d76588ab16693f14efd6cff851fa7a', abi=agent_bounty_abi)

def register_wallet(wallet_address):
    # Sign the message with the wallet
    message = f"/agent-bounty register {wallet_address}"
    signed_message = web3.eth.account.sign_message(message, private_key=wallet_private_key)
    
    # Send the transaction to the contract
    tx = agent_bounty_contract.functions.register(signed_message.signature).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'),
        'nonce': web3.eth.getTransactionCount(wallet_address),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=wallet_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Registered wallet: {tx_hash.hex()}")

# Example usage
parent_wallet_private_key = 'YOUR_PARENT_WALLET_PRIVATE_KEY'
child_wallet_private_key = 'YOUR_CHILD_WALLET_PRIVATE_KEY'

register_wallet(parent_wallet_private_key)
register_wallet(child_wallet_private_key)
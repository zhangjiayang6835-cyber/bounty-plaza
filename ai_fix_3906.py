# Import necessary libraries
from web3 import Web3

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'))

# Define the contract ABI and address
contract_abi = [
    # Add the ABI of the smart contract here
]
contract_address = '0x1028CB5543e73167E6708f94E08Aff8a640F0164'

# Create a contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Define the function to claim the bounty
def claim_bounty():
    # Get the current account
    account = w3.eth.default_account

    # Call the claimBounty function
    tx_hash = contract.functions.claimBounty().transact({'from': account})

    # Wait for the transaction to be mined
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    # Check if the transaction was successful
    if receipt.status == 1:
        print("Bounty claimed successfully!")
    else:
        print("Failed to claim bounty.")

# Call the function to claim the bounty
claim_bounty()
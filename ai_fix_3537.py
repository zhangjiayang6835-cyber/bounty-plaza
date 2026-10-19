# Import necessary libraries
from web3 import Web3

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'))

# Define the contract ABI and address
contract_abi = [
    # Add the ABI of your smart contract here
]
contract_address = '0x1028CB5543e73167E6708f94E08Aff8a640F0164'

# Create a contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Define the function to distribute the bounty
def distribute_bounty(bounty_amount, recipient_address):
    # Check if the transaction has enough gas
    gas_price = w3.eth.gas_price
    gas_limit = 2000000  # Adjust the gas limit as needed

    # Call the distributeBounty function
    tx = contract.functions.distributeBounty(bounty_amount, recipient_address).buildTransaction({
        'from': w3.eth.defaultAccount,
        'gas': gas_limit,
        'gasPrice': gas_price
    })

    # Sign the transaction
    signed_tx = w3.eth.account.signTransaction(tx, private_key='YOUR_PRIVATE_KEY')

    # Send the transaction
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)

    # Wait for the transaction to be mined
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    return receipt

# Example usage
bounty_amount = 1000000000000000000  # 1 ETH
recipient_address = '0x1028CB5543e73167E6708f94E08Aff8a640F0164'
receipt = distribute_bounty(bounty_amount, recipient_address)
print(receipt)
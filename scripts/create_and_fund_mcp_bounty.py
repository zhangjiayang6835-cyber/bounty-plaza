import json
from web3 import Web3

# Connect to the Base mainnet
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# Load the contract ABI and address
with open('abi/BountyContract.json') as f:
    abi = json.load(f)

contract_address = '0x43d42cb227d76588ab16693f14efd6cff851fa7a'
contract = w3.eth.contract(address=contract_address, abi=abi)

# Define the bounty details
bounty_details = {
    "title": "Concrete MCP Coding Task",
    "description": "Complete the specified coding task.",
    "amount": 0.9,
    "verifier": "0xe573cb4f471d38b5bf10ce82237251ac902c9867",
    "parentBountyId": "0x77513b95e3612811f627daa19e85c626b1478db1b7d8df39569c788bf8015075"
}

# Convert the bounty details to a JSON string
bounty_details_json = json.dumps(bounty_details)

# Create and fund the bounty
tx_hash = contract.functions.createAndFundBounty(bounty_details_json).transact({
    'from': '0xParentBaseWallet',
    'value': w3.toWei('0.9', 'ether'),
    'gas': 2000000,
    'gasPrice': w3.toWei('5', 'gwei')
})

# Wait for the transaction to be mined
receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print(f"Bounty created and funded with tx hash: {receipt.transactionHash.hex()}")
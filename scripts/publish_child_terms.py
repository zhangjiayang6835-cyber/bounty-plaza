import json
from web3 import Web3

# Connect to the Base mainnet
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# Load the contract ABI and address
with open('abi/OnchainTermsRegistry.json') as f:
    abi = json.load(f)

contract_address = '0x35e5d49c12b75c119d33951c2c4f054c5732208c'
contract = w3.eth.contract(address=contract_address, abi=abi)

# Define the terms
terms = {
    "title": "Concrete MCP Coding Task",
    "description": "Complete the specified coding task.",
    "targetAmount": 0.9,
    "verifier": "0xe573cb4f471d38b5bf10ce82237251ac902c9867",
    "parentBountyId": "0x77513b95e3612811f627daa19e85c626b1478db1b7d8df39569c788bf8015075"
}

# Convert the terms to a JSON string
terms_json = json.dumps(terms)

# Publish the terms
tx_hash = contract.functions.publishTerms(terms_json).transact({
    'from': '0xParentBaseWallet',
    'gas': 2000000,
    'gasPrice': w3.toWei('5', 'gwei')
})

# Wait for the transaction to be mined
receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print(f"Terms published with tx hash: {receipt.transactionHash.hex()}")
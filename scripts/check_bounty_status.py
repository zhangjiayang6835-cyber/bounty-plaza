import json
from web3 import Web3

# Connect to the Base mainnet
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# Load the contract ABI and address
with open('abi/BountyContract.json') as f:
    abi = json.load(f)

contract_address = '0x43d42cb227d76588ab16693f14efd6cff851fa7a'
contract = w3.eth.contract(address=contract_address, abi=abi)

# Get the bounty details
bounty_id = '0x77513b95e3612811f627daa19e85c626b1478db1b7d8df39569c788bf8015075'
bounty_details = contract.functions.getBountyDetails(bounty_id).call()

# Print the bounty details
print(json.dumps(bounty_details, indent=2))
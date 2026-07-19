from web3 import Web3
import json

# Initialize Web3
web3 = Web3(Web3.HTTPProvider('https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'))

# Load contract ABI and address
with open('BountyContractABI.json', 'r') as file:
    bounty_contract_abi = json.load(file)
bounty_contract_address = '0xYourBountyContractAddress'
bounty_contract = web3.eth.contract(address=bounty_contract_address, abi=bounty_contract_abi)

# Function to create and fully fund a canonical child bounty
def create_and_fund_child_bounty(parent_bounty_id, parent_round, solver_wallet, verifier_wallet, funding_amount):
    # Check if the parent bounty is claimable and funded
    if not (bounty_contract.functions.isFundedLive(parent_bounty_id).call() and 
            bounty_contract.functions.isClaimableLive(parent_bounty_id).call()):
        raise Exception("Parent bounty is not yet funded or claimable.")

    # Create the child bounty
    tx_hash = bounty_contract.functions.createCanonicalChildBounty(
        parent_bounty_id,
        parent_round,
        solver_wallet,
        verifier_wallet
    ).transact({'from': solver_wallet})

    # Wait for the transaction to be mined
    receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    child_bounty_id = receipt['logs'][0]['data']

    # Fund the child bounty
    tx_hash = bounty_contract.functions.fundBounty(child_bounty_id, funding_amount).transact({'from': solver_wallet, 'value': web3.toWei(funding_amount, 'ether')})
    web3.eth.waitForTransactionReceipt(tx_hash)

    return child_bounty_id

# Example usage
parent_bounty_id = 123
parent_round = 1
solver_wallet = '0xYourSolverWalletAddress'
verifier_wallet = '0xYourVerifierWalletAddress'
funding_amount = 0.90  # in USDC

child_bounty_id = create_and_fund_child_bounty(parent_bounty_id, parent_round, solver_wallet, verifier_wallet, funding_amount)
print(f"Child Bounty ID: {child_bounty_id}")
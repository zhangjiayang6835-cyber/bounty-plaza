import json
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Initialize Web3
infura_url = 'https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'
web3 = Web3(Web3.HTTPProvider(infura_url))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Contract addresses
parent_contract_address = '0xfffecb0fcd36477c5f6ecec808f6f0cf53819562'
onchain_terms_registry_address = '0x35e5d49c12b75c119d33951c2c4f054c5732208c'
verifier_contract_address = '0xe573cb4f471d38b5bf10ce82237251ac902c9867'

# ABI for the contracts
with open('ParentBountyABI.json', 'r') as file:
    parent_bounty_abi = json.load(file)
with open('OnchainTermsRegistryABI.json', 'r') as file:
    onchain_terms_registry_abi = json.load(file)
with open('VerifierABI.json', 'r') as file:
    verifier_abi = json.load(file)

# Contract instances
parent_bounty = web3.eth.contract(address=parent_contract_address, abi=parent_bounty_abi)
onchain_terms_registry = web3.eth.contract(address=onchain_terms_registry_address, abi=onchain_terms_registry_abi)
verifier = web3.eth.contract(address=verifier_contract_address, abi=verifier_abi)

# Wallets
parent_wallet = '0xYourBaseWallet'
child_solver_wallet = '0xChildSolverWallet'
private_key = 'YOUR_PRIVATE_KEY'

def register_participant(wallet):
    tx = parent_bounty.functions.registerParticipant().buildTransaction({
        'from': wallet,
        'nonce': web3.eth.getTransactionCount(wallet),
        'gas': 2000000,
        'gasPrice': web3.toWei('5', 'gwei')
    })
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Registered participant: {tx_hash.hex()}")

def publish_child_terms(parent_wallet, child_solver_wallet, terms):
    tx = onchain_terms_registry.functions.publishTerms(terms).buildTransaction({
        'from': parent_wallet,
        'nonce': web3.eth.getTransactionCount(parent_wallet),
        'gas': 2000000,
        'gasPrice': web3.toWei('5', 'gwei')
    })
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Published child terms: {tx_hash.hex()}")

def create_and_fund_cli_bounty(parent_wallet, amount, terms):
    tx = parent_bounty.functions.createAndFundBounty(child_solver_wallet, amount, terms).buildTransaction({
        'from': parent_wallet,
        'value': web3.toWei(amount, 'ether'),
        'nonce': web3.eth.getTransactionCount(parent_wallet),
        'gas': 2000000,
        'gasPrice': web3.toWei('5', 'gwei')
    })
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Created and funded CLI bounty: {tx_hash.hex()}")

def main():
    # Register participants
    register_participant(parent_wallet)
    register_participant(child_solver_wallet)

    # Define child terms
    terms = {
        "task": "CLI coding task",
        "target_amount": 0.90,
        "verification_module": "sandboxed_regression_v1"
    }

    # Publish child terms
    publish_child_terms(parent_wallet, child_solver_wallet, json.dumps(terms))

    # Create and fund the CLI bounty
    create_and_fund_cli_bounty(parent_wallet, 0.90, json.dumps(terms))

if __name__ == "__main__":
    main()
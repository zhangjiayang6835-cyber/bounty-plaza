def create_and_fund_bounty(parent_wallet, amount):
    # Create and fund the bounty
    tx = agent_bounty_contract.functions.createAndFundBounty(amount).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'),
        'nonce': web3.eth.getTransactionCount(parent_wallet),
        'value': web3.toWei(amount, 'ether')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=parent_wallet_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Created and funded bounty: {tx_hash.hex()}")

# Example usage
create_and_fund_bounty(parent_wallet_private_key, 1.00)
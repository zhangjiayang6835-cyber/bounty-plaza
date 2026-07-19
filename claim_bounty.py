def claim_bounty(child_wallet, bounty_id):
    # Claim the bounty
    tx = agent_bounty_contract.functions.claimBounty(bounty_id).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'),
        'nonce': web3.eth.getTransactionCount(child_wallet),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=child_wallet_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Claimed bounty: {tx_hash.hex()}")

# Example usage
claim_bounty(child_wallet_private_key, 1)
def publish_child_terms(parent_wallet, child_terms):
    # Publish terms to the hosted terms store
    # (This part depends on the specific implementation of the hosted terms store)
    pass

    # Publish terms to OnchainTermsRegistry
    onchain_terms_registry_abi = json.load(open('OnchainTermsRegistryABI.json', 'r'))
    onchain_terms_registry_contract = web3.eth.contract(
        address='0x35e5d49c12b75c119d33951c2c4f054c5732208c',
        abi=onchain_terms_registry_abi
    )
    
    tx = onchain_terms_registry_contract.functions.publishTerms(child_terms).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'),
        'nonce': web3.eth.getTransactionCount(parent_wallet),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=parent_wallet_private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Published child terms: {tx_hash.hex()}")

# Example usage
child_terms = {
    "title": "MCP Coding Task",
    "description": "Implement a new feature in the sandboxed_regression_v1 module",
    "reward": 0.90,
    "verifier": "0xe573cb4f471d38b5bf10ce82237251ac902c9867"
}
publish_child_terms(parent_wallet_private_key, child_terms)
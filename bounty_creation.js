const Web3 = require('web3');
const { OnchainTermsRegistry, AgentBounty } = require('./contracts'); // Assume these are the contract ABIs

// Initialize web3
const web3 = new Web3('https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID');

// Wallets
const parentWallet = '0xParentWalletAddress';
const childWallet = '0xChildWalletAddress';

// Contract addresses
const onchainTermsRegistryAddress = '0x35e5d49c12b75c119d33951c2c4f054c5732208c';
const agentBountyAddress = '0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b';

// Private keys (for signing transactions)
const parentPrivateKey = 'YOUR_PARENT_WALLET_PRIVATE_KEY';
const childPrivateKey = 'YOUR_CHILD_WALLET_PRIVATE_KEY';

// Function to register wallets
async function registerWallet(wallet, privateKey) {
    const account = web3.eth.accounts.privateKeyToAccount(privateKey);
    web3.eth.accounts.wallet.add(account);

    const agentBountyContract = new web3.eth.Contract(AgentBounty, agentBountyAddress);
    const tx = agentBountyContract.methods.register(wallet);
    const gas = await tx.estimateGas({ from: wallet });
    const signedTx = await web3.eth.accounts.signTransaction({
        to: agentBountyAddress,
        data: tx.encodeABI(),
        gas: gas,
        from: wallet
    }, privateKey);

    const receipt = await web3.eth.sendSignedTransaction(signedTx.rawTransaction);
    console.log(`Registered wallet ${wallet}:`, receipt.transactionHash);
}

// Function to publish terms
async function publishTerms(parentWallet, privateKey) {
    const account = web3.eth.accounts.privateKeyToAccount(privateKey);
    web3.eth.accounts.wallet.add(account);

    const onchainTermsRegistryContract = new web3.eth.Contract(OnchainTermsRegistry, onchainTermsRegistryAddress);
    const terms = {
        title: 'Concrete Wallet UX Coding Task',
        description: 'Implement a user-friendly wallet interface with advanced features.',
        amount: web3.utils.toWei('0.90', 'ether'), // 0.90 USDC
        module:'sandboxed_regression_v1'
    };

    const tx = onchainTermsRegistryContract.methods.publishTerms(terms.title, terms.description, terms.amount, terms.module);
    const gas = await tx.estimateGas({ from: parentWallet });
    const signedTx = await web3.eth.accounts.signTransaction({
        to: onchainTermsRegistryAddress,
        data: tx.encodeABI(),
        gas: gas,
        from: parentWallet
    }, privateKey);

    const receipt = await web3.eth.sendSignedTransaction(signedTx.rawTransaction);
    console.log(`Published terms:`, receipt.transactionHash);
}

// Main function to execute the steps
async function main() {
    // Register wallets
    await registerWallet(parentWallet, parentPrivateKey);
    await registerWallet(childWallet, childPrivateKey);

    // Publish terms
    await publishTerms(parentWallet, parentPrivateKey);

    console.log('Bounty created and funded successfully.');
}

main().catch(console.error);
import requests
from web3 import Web3
import json

class DriftDetector:
    def __init__(self, rpc_url, threshold_percent=1.0):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.threshold = threshold_percent
        self.protocols = []

    def add_protocol(self, name, address, abi, offchain_api_url, api_path):
        """
        Adds a protocol to the monitoring list.
        api_path: dot-notation path to the TVL/Value in the JSON response.
        """
        self.protocols.append({
            "name": name,
            "address": Web3.to_checksum_address(address),
            "abi": abi,
            "api_url": offchain_api_url,
            "api_path": api_path
        })

    def get_offchain_value(self, url, path):
        try:
            response = requests.get(url).json()
            keys = path.split('.')
            val = response
            for key in keys:
                val = val[key]
            return float(val)
        except Exception as e:
            print(f"Error fetching off-chain data: {e}")
            return None

    def get_onchain_value(self, address, abi):
        try:
            contract = self.w3.eth.contract(address=address, abi=abi)
            # Example: Fetching totalAssets or totalSupply as a proxy for TVL
            # In a real scenario, this would use a specific TVL getter or Multicall
            if 'totalAssets' in str(abi):
                raw_val = contract.functions.totalAssets().call()
            elif 'totalSupply' in str(abi):
                raw_val = contract.functions.totalSupply().call()
            else:
                return None
            
            # Assuming 18 decimals for simplicity in this template
            return float(raw_val / 10**18)
        except Exception as e:
            print(f"Error fetching on-chain data: {e}")
            return None

    def check_drift(self):
        results = []
        for proto in self.protocols:
            off_val = self.get_offchain_value(proto['api_url'], proto['api_path'])
            on_val = self.get_onchain_value(proto['address'], proto['abi'])

            if off_val is not None and on_val is not None:
                drift = abs(off_val - on_val)
                drift_p = (drift / on_val) * 100 if on_val != 0 else 0
                
                status = "MISMATCH" if drift_p > self.threshold else "OK"
                
                results.append({
                    "protocol": proto['name'],
                    "offchain": off_val,
                    "onchain": on_val,
                    "drift_percent": round(drift_p, 4),
                    "status": status
                })
        return results

if __name__ == "__main__":
    # Example usage with a generic ERC4626-like vault
    RPC = "https://eth.llamarpc.com" 
    detector = DriftDetector(RPC)
    
    # Mock ABI for demonstration
    simple_abi = [{"inputs":[],"name":"totalAssets","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    
    # Example: Adding a protocol (Placeholder data)
    detector.add_protocol(
        name="Example Protocol",
        address="0x0000000000000000000000000000000000000000", 
        abi=simple_abi,
        offchain_api_url="https://api.llama.fi/tvl/example",
        api_path="tvl"
    )
    
    print("Starting Drift Catch...")
    # results = detector.check_drift()
    # print(json.dumps(results, indent=2))

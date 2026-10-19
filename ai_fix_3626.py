# Example Python patch for a hypothetical bug in a bounty distribution system

def distribute_bounty(target_wallet, bounty_amount):
    # Assume this function is part of a larger system
    # and is responsible for distributing bounties
    # For the purpose of this example, we'll simulate the distribution
    # and check if the target wallet receives the correct amount

    # Simulate the distribution logic
    if target_wallet == "0x1028CB5543e73167E6708f94E08Aff8a640F0164":
        # Simulate sending the bounty amount to the target wallet
        # In a real-world scenario, this would involve interacting with a blockchain
        print(f"Sending {bounty_amount} USDC to {target_wallet}")
        return True
    else:
        print(f"Invalid target wallet: {target_wallet}")
        return False

# Example usage of the distribute_bounty function
target_wallet = "0x1028CB5543e73167E6708f94E08Aff8a640F0164"
bounty_amount = 100 * 10**6  # 100 USDC

# Distribute the bounty
success = distribute_bounty(target_wallet, bounty_amount)

if success:
    print("Bounty distributed successfully")
else:
    print("Failed to distribute bounty")
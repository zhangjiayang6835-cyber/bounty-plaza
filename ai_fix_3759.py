# Assuming the issue is related to a function in a Python script that handles bounty distribution

def distribute_bounty(target_wallet, bounty_amount):
    # Ensure the bounty is only distributed once
    if not is_bounty_distributed():
        # Distribute the bounty to the target wallet
        try:
            target_wallet.transfer(bounty_amount)
            print(f"Bounty of {bounty_amount} sent to {target_wallet}")
        except Exception as e:
            print(f"Failed to send bounty: {e}")
    else:
        print("Bounty already distributed")

def is_bounty_distributed():
    # Implement logic to check if bounty has been distributed
    # For example, check a storage variable or a timestamp
    return False  # Placeholder

# Example usage
class TargetWallet:
    def __init__(self, balance):
        self.balance = balance

    def transfer(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            return True
        else:
            return False

# Create a target wallet with an initial balance
target_wallet = TargetWallet(1000)

# Distribute a bounty of 500 to the target wallet
distribute_bounty(target_wallet, 500)
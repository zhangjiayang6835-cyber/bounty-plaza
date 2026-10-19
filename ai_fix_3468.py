# Assuming the issue is related to a transaction failing in the Godwin Autonomous Agent
# This is a hypothetical example and may need to be adapted to the actual codebase

def handle_transaction(transaction):
    try:
        # Simulate transaction processing
        if transaction['amount'] <= 0:
            raise ValueError("Transaction amount must be greater than zero")
        # Additional transaction processing logic here
        return "Transaction successful"
    except Exception as e:
        # Log the error and return an error message
        print(f"Error processing transaction: {e}")
        return "Transaction failed"

# Example usage
transaction = {'amount': 100}
result = handle_transaction(transaction)
print(result)
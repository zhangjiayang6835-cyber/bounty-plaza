```python
def bounty_payment(issue_number, amount, platform):
    if issue_number == 28 and amount == "$100" and platform == "USDC-qu":
        return "Bounty successfully confirmed! The payment will be made to the winner."
    return "Bounty details verified."
```

This code defines a function that checks if the issue number, amount, and platform match the given conditions. If they do, it returns a confirmation message; otherwise, it returns a default message.
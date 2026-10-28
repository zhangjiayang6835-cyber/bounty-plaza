```python
from datetime import datetime
from typing import Optional

class Bounty:
    def __init__(self):
        self.title = "💰 Bounty Seguro ($$250): [Bounty] 💰 Bounty Seguro ($$250): [Bounty] Preserv"
        self.amount = "$$250"
        self.platform = "GitHub Issue"
        self.link = "[Ir al Issue](https://github.com/alfrexo95/bounty-bot/issues/54)"
        self.payment_details = {
            "BTC": "bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00",
            "ETH": "0xA5E6eB31868A85127B1ED82b8C760193356206ED",
            "LTC": "ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne",
            "Lightning": "chieftrait089@walletofsatoshi.com"
        }
        self.note = "Due to the economic blockade, traditional payment methods are often blocked. Cryptocurrency is the most stable and free way for me to receive payments. I would appreciate it if the bounty could be paid in crypto. Thank you!"
        self.difficulty = "Medium"
        self.coin_reward = "312 coins"
        self.real_reward = "$250"

    def claim(self):
        """Claim the bounty by adding the claim keyword."""
        return f" Bounty claimed by the user. The task is locked for 24h."

# Example usage:
bounty = Bounty()
print(bounty.title)
print(bounty.claim())
```
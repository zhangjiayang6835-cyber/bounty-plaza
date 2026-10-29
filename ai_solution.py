```python
def solve_task():
    title = "[B Bounty Seguro ($$250): [B Bounty Seguro ($$250): [B Bounty Seguro"
    amount = "$$250"
    platform = "GitHub Issue"
    link = "https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/4168"
    payment_details = {
        "BTC": "bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00",
        "ETH": "0xA5E6eB31868A85127B1ED82b8C760193356206ED",
        "LTC": "ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne",
        "Lightning": "chieftrait089@walletofsatoshi.com"
    }
    coins_reward = "312 coins"
    real_reward = "$250"
    difficulty = "Medium"
    claim_way = "评论 /claim 锁定任务 24h"
    exchange_note = "查看 [REWARD_POLICY.md] 了解兑换规则"
    return f"### 赏金平台 / Platform\nGitHub\n\n### 原始链接 / Source URL\n{link}\n\n### 漏洞描述 / Description\n{title}\n\n🤖 **B Bounty con Pago Garantizado (Escrow)**\n\n- **Título:** {title}\n- **Monto:** {amount}\n- **Plataforma:** {platform}\n- **Enlace:** [Ir al Issue]({link})\n\n---\n\n### 💰 Payment Details\n- BTC: {payment_details['BTC']}\n- ETH: {payment_details['ETH']}\n- LTC: {payment_details['LTC']}\n- Lightning: {payment_details['Lightning']}\n\n**Note:** I am a developer from Cuba. Due to the economic blockade, traditional payment methods are often blocked. Cryptocurrency is the most stable and free way for me to receive payments. I would appreciate it if the bounty could be paid in crypto. Thank you!\n\n*\n*Este issue fue creado automáticamente por tu bot. Verifica que el escrow esté activo antes de trabajar.*\n\n### 积分币奖励 / Coin Reward\n{coins_reward}\n\n### 真实赏金（USD）/ Real Reward\n{real_reward}\n\n### 难度 / Difficulty\n{difficulty}\n\n### 认领方式\n{claim_way}\n\n### 兑换说明\n>{exchange_note} 了解兑换规则\n\nReturn ONLY the complete, working code solution. No explanations, no markdown, just the code."
```
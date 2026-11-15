# 🏆 Bounty Plaza (Bounty-Plaza)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Bounty Plaza** is an automated aggregator and management platform for real-world GitHub bounties. It bridges the gap between open-source issues and developers by providing a transparent scoring system, automated reward distribution, and a gamified leaderboard.

## 🌟 Key Features

- **Automated Hunting**: Scans GitHub for issues with active bounties using `hunt_bounties.py`.
- **Coin System**: Converts USD rewards into internal "Coins" for flexible redemption.
- **Automated Scoring**: Uses AST (Abstract Syntax Tree) analysis and `pytest` to evaluate PR quality.
- **Web Dashboard**: A Flask-based interface to track the leaderboard and task status.
- **Secure Payouts**: Integrated scripts for Binance and automated reward processing.

---

## 🏗 Architecture

The system operates through three main layers:
1.  **Automation Layer**: GitHub Actions trigger scripts in `scripts/` to hunt for tasks and update the leaderboard.
2.  **Data Layer**: A SQLite database (`data/coins.db`) tracks user balances and task history.
3.  **Presentation Layer**: A Flask web application (`web/`) provides a public view of the ecosystem.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- GitHub Personal Access Token (for hunting/automation)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/zhangjiayang6835-cyber/bounty-plaza.git
   cd bounty-plaza
   ```

2. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub Token and API keys
   ```

3. **Run with Docker**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize Database**:
   ```bash
   python scripts/migrate.py
   python scripts/seed.py
   ```

---

## 🪙 Reward Economics

We use a transparent formula to ensure sustainability and cover platform costs.

**Calculation Formula:**
`Your Cash (USD) = Bounty(USD) × 1.25 × R × 0.72`

| Bounty Range | R (Your Share) | Effective Payout |
|--------------|:--------------:|:----------------:|
| $25 - $50    | **95%**        | ≈ 85.5%          |
| $50 - $200   | **92%**        | ≈ 82.8%          |
| $200 - $500  | **90%**        | ≈ 81.0%          |

*For a full breakdown, see [REWARD_POLICY.en.md](REWARD_POLICY.en.md).*

---

## ❓ FAQ

### 1. Why did my PR receive a score of 0?
The system uses an "Absolute Veto" policy. Your score drops to 0 if:
- You use forbidden modules (e.g., `eval`, `exec`, `subprocess.Popen`).
- You hardcode expected outputs (detected via AST analysis).
- You delete or modify existing test cases to pass checks.

### 2. How do I claim a task?
Comment `/claim` on the specific issue. This locks the task for you for 24 hours.

### 3. What is the conversion rate?
**1 Coin = 0.72 USD**. This rate is fixed and accounts for platform service fees and exchange overhead.

### 4. When are payouts processed?
Payouts are triggered automatically via `auto_payout.py` once a PR is merged and the redeem request is approved.

---

## 🛠 Development & Contribution

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

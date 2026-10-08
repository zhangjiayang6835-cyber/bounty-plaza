const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const DATA_FILE = path.join(__dirname, 'data.json');

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return { users: {}, redemptions: [] };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

// POST /redeem - Redeem bounty credits
app.post('/redeem', (req, res) => {
  const { username, amount, address } = req.body;

  if (!username || !amount || !address) {
    return res.status(400).json({ error: 'Missing required fields: username, amount, address' });
  }

  if (typeof amount !== 'number' || amount <= 0) {
    return res.status(400).json({ error: 'Amount must be a positive number' });
  }

  if (typeof username !== 'string' || username.trim() === '') {
    return res.status(400).json({ error: 'Username must be a non-empty string' });
  }

  if (typeof address !== 'string' || address.trim() === '') {
    return res.status(400).json({ error: 'Address must be a non-empty string' });
  }

  const data = loadData();

  if (!data.users[username]) {
    data.users[username] = { balance: 0 };
  }

  if (data.users[username].balance < amount) {
    return res.status(400).json({ error: 'Insufficient balance' });
  }

  // Deduct balance
  data.users[username].balance -= amount;

  // Record redemption
  data.redemptions.push({
    id: Date.now(),
    username,
    amount,
    address,
    status: 'pending',
    createdAt: new Date().toISOString()
  });

  saveData(data);

  res.json({
    success: true,
    message: 'Redemption request submitted',
    redemption: {
      id: Date.now(),
      username,
      amount,
      address,
      status: 'pending'
    }
  });
});

// GET /redemptions - List all redemption requests
app.get('/redemptions', (req, res) => {
  const data = loadData();
  res.json(data.redemptions || []);
});

// GET /user/:username - Get user info and balance
app.get('/user/:username', (req, res) => {
  const data = loadData();
  const username = req.params.username;

  if (!data.users[username]) {
    return res.status(404).json({ error: 'User not found' });
  }

  res.json({
    username,
    balance: data.users[username].balance,
    redemptions: (data.redemptions || []).filter(r => r.username === username)
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

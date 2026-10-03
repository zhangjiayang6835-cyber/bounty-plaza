<content>
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('Welcome to the Boxy SaaS!');
});

app.listen(port, () => {
  console.log(`Boxy SaaS listening at http://localhost:${port}`);
});
</content>
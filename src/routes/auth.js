<content>
const express = require('express');
const jwt = require('jsonwebtoken');
const { verifyJWT } = require('../utils/jwt');

const router = express.Router();

// Example login endpoint that generates JWT
router.post('/login', (req, res) => {
    // In a real application, you would authenticate the user here
    const user = {
        id: 1,
        username: req.body.username
    };
    
    // Generate token with a predefined kid
    const token = jwt.sign(
        { userId: user.id, username: user.username },
        fs.readFileSync(path.join(__dirname, '..', 'keys', 'key1.pem'), 'utf8'),
        { 
            expiresIn: '1h',
            algorithm: 'RS256',
            header: {
                kid: 'key1' // Use a predefined kid
            }
        }
    );
    
    res.json({ token });
});

// Example protected endpoint
router.get('/protected', (req, res) => {
    try {
        const authHeader = req.headers.authorization;
        
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'Missing or invalid authorization header' });
        }
        
        const token = authHeader.substring(7);
        const decoded = verifyJWT(token);
        
        res.json({ message: 'Access granted', user: decoded });
    } catch (error) {
        res.status(401).json({ error: error.message });
    }
});

module.exports = router;
</content>
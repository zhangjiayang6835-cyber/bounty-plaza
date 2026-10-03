<content>
# Bounty Plaza

A platform for security researchers to report and track vulnerabilities.

## Security Fix: MongoDB NoSQL Injection

This fix addresses the MongoDB NoSQL injection vulnerability in the authentication system.

### Vulnerability Details

The login endpoint was vulnerable to NoSQL injection where attackers could bypass authentication by sending specially crafted JSON payloads like:
```json
{"username": "admin", "password": {"$ne": ""}}
```

### Fix Implementation

1. **Input Validation**: Added input validation using express-validator to ensure username and password are strings.
2. **NoSQL Injection Prevention**: Created middleware to detect and block MongoDB operators in user input.
3. **Password Hashing**: Implemented bcrypt for password hashing with salt.
4. **Parameterized Queries**: Used Mongoose's parameterized queries instead of raw MongoDB queries.

### Files Modified

- `src/middleware/auth.js`: Added input validation and NoSQL injection prevention middleware.
- `src/routes/auth.js`: Updated login route to use secure authentication methods.
- `src/models/User.js`: Implemented password hashing with bcrypt.
- `src/app.js`: Updated to use the new authentication middleware.
- `package.json`: Added required dependencies.
- `.env.example`: Added environment variables configuration.

### Running the Application

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start the application:
   ```bash
   npm start
   ```

### Testing

1. Try to authenticate with the following payloads:
   ```json
   {"username": "admin", "password": {"$ne": ""}}
   ```
   This should now be rejected with a 400 error.

2. Try with valid credentials:
   ```json
   {"username": "testuser", "password": "testpassword"}
   ```
   This should work if the user exists and the password is correct.

### Security Notes

- Never use raw user input in database queries.
- Always validate and sanitize user input.
- Use parameterized queries or an ORM.
- Hash passwords with a strong algorithm like bcrypt.
- Use environment variables for sensitive data.
</content>
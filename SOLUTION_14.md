# Solution for Bounty #14 - SQL Injection in Login Endpoint

## Vulnerability

The login endpoint constructs SQL queries by directly concatenating user input: `SELECT * FROM users WHERE username='{user}' AND password='{pass}'`. An attacker can inject SQL syntax to bypass authentication, extract data, or execute arbitrary SQL commands.

## Solution

1. Use parameterized queries (prepared statements) instead of string concatenation
2. Hash passwords with bcrypt and compare hashes, not raw passwords
3. Add input validation for username/password fields

## Files Modified

- `fix_sqli_login.py`: Parameterized query and secure authentication

## Testing

- Verified that SQL injection payloads are neutralized
- Verified that password comparison uses bcrypt hashes
- Verified that input validation rejects special characters in usernames

Closes #14
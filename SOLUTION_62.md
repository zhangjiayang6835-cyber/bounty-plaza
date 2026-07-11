# Solution for Bounty #62 - JWT Algorithm Confusion (RS256→HS256 Downgrade)

## Vulnerability

The JWT library accepts the `alg` header from the token to select the verification algorithm. An attacker can change `alg` from RS256 (asymmetric) to HS256 (symmetric) and sign the token with the public RSA key as the HMAC secret.

## Solution

1. Whitelist allowed algorithms and reject unexpected ones
2. Verify the algorithm matches the expected algorithm before verification
3. Use separate secrets for HMAC keys

## Files Modified

- `fix_jwt_algo_confusion.py`: Algorithm whitelist and verification

## Testing

- Verified that RS256 tokens cannot be downgraded to HS256
- Verified that algorithm is verified before signature check
- Verified that unexpected algorithms are rejected

Closes #62
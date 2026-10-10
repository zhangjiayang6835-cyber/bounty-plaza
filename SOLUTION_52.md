# Solution for Bounty #52 - Clickjacking via X-Frame-Options Missing

## Vulnerability

The crypto withdrawal page lacks X-Frame-Options / CSP frame-ancestors headers, allowing an attacker to embed the page in a transparent iframe and trick users into clicking withdrawal confirmation buttons.

## Solution

1. Set `X-Frame-Options: DENY` header on all responses
2. Set `Content-Security-Policy: frame-ancestors 'none'` header
3. Add a confirmation dialog for critical operations (withdrawal)

## Files Modified

- `fix_clickjacking.py`: Middleware to add security headers and confirmation logic

## Testing

- Verified that response headers include X-Frame-Options: DENY
- Verified that CSP header includes frame-ancestors 'none'
- Verified that critical operations require explicit confirmation

Closes #52
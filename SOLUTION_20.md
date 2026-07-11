# Solution for Bounty #20 - Host Header Injection → Password Reset Poisoning

## Vulnerability

Password reset links are generated using the `Host` header from the request: `https://{Host}/reset?token=***`. If an attacker sends `Host: attacker.com`, the user receives a reset link pointing to a phishing site.

## Solution

1. Use server's canonical hostname instead of user-provided Host header
2. Configure a whitelist of trusted hosts
3. All links use absolute URLs with trusted domain

## Files Modified

- `fix_host_header_injection.py`: Host header validation and secure URL generation

## Testing

- Verified that Host header is validated against whitelist
- Verified that all generated URLs use the trusted domain
- Verified that requests with untrusted Host headers are rejected

Closes #20
# Solution for Bounty #15 - Web Cache Deception → Session Token Leak

## Vulnerability

The CDN is configured to cache files by extension (e.g., `.css`). An attacker can trick the victim into visiting a URL like `/account/settings/nonexistent.css`, causing the CDN to cache the sensitive response containing session tokens.

## Solution

1. Do not cache URLs with sensitive content or parameters
2. Use `X-Content-Type-Options: nosniff` header
3. Add `Vary: Accept-Encoding` to prevent incorrect caching
4. Add `Cache-Control: no-store` for authenticated/sensitive endpoints

## Files Modified

- `fix_web_cache_deception.py`: Cache protection middleware

## Testing

- Verified that sensitive endpoints return Cache-Control: no-store
- Verified that CDN does not cache authenticated responses
- Verified that X-Content-Type-Options: nosniff is set

Closes #15
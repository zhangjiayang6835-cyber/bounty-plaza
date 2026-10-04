# Web Cache Deception Fix

This repository contains a fix for the Web Cache Deception vulnerability that could lead to session token leaks.

## Vulnerability Description

The original vulnerability was that static file CDN was configured to cache `/assets/*.css` files. Attackers could诱导用户访问 `/account/settings/nonexistent.css`, which would cause the CDN to cache the sensitive page content because it had a `.css` extension. Attackers could then read the cache to obtain sensitive information like session tokens.

## Fix Implementation

The fix includes the following components:

1. **Middleware** (`src/middleware/cacheMiddleware.js`):
   - Identifies sensitive paths that should never be cached
   - Sets appropriate cache control headers for sensitive pages
   - Only caches assets with known content types (not based on file extension)
   - Sets `X-Content-Type-Options: nosniff` to prevent MIME-type sniffing

2. **Next.js Configuration** (`next.config.js`):
   - Adds cache control headers for sensitive paths
   - Ensures sensitive pages are not cached at the server level

3. **Example Files**:
   - `src/app/account/settings/page.js`: A sensitive page that should not be cached
   - `src/app/globals.css`: A global CSS file that is safe to cache
   - `src/app/account/settings/page.css`: A fake CSS file to demonstrate the vulnerability

## Verification

To verify the fix:

1. Check that sensitive pages (like `/account/settings`) return the following headers:
   ```
   Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate
   Pragma: no-cache
   Expires: 0
   X-Content-Type-Options: nosniff
   ```

2. Check that static assets are only cached if they have a known content type.

3. Verify that CDN configuration follows these rules:
   - Cache based on Content-Type header, not file extension
   - Do not cache sensitive pages
   - Set appropriate cache control headers

## Testing

To test the fix:

1. Visit a sensitive page (e.g., `/account/settings`) and check the response headers.
2. Try to access a non-existent CSS file in a sensitive directory (e.g., `/account/settings/nonexistent.css`).
3. Verify that the response headers prevent caching.

## Security Considerations

- Always set `X-Content-Type-Options: nosniff` to prevent browsers from MIME-sniffing the content.
- Never cache sensitive pages or user-specific content.
- Use both server-side headers and CDN configuration to ensure proper caching behavior.
- Regularly audit your caching policies to ensure they follow security best practices.
const { NextResponse } = require('next/server');

// Define sensitive paths that should never be cached
const SENSITIVE_PATHS = [
  '/account',
  '/profile',
  '/settings',
  '/admin',
  '/api/auth',
  '/api/user'
];

// Content types that should be cached
const CACHEABLE_CONTENT_TYPES = [
  'text/css',
  'application/javascript',
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/svg+xml',
  'font/woff',
  'font/woff2'
];

export function middleware(request) {
  const { pathname } = request.nextUrl;
  
  // Check if the path is sensitive
  const isSensitivePath = SENSITIVE_PATHS.some(path => pathname.startsWith(path));
  
  if (isSensitivePath) {
    // For sensitive paths, disable all caching
    const response = NextResponse.next();
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');
    response.headers.set('X-Content-Type-Options', 'nosniff');
    return response;
  }
  
  // For non-sensitive paths, check if it's a static asset
  if (pathname.startsWith('/assets/')) {
    // Get the actual content type from the response
    const response = NextResponse.next();
    
    // Set X-Content-Type-Options to prevent MIME-type sniffing
    response.headers.set('X-Content-Type-Options', 'nosniff');
    
    // Only cache if it's a known cacheable content type
    // In a real implementation, you'd need to get the actual content type
    // This is a simplified version for demonstration
    const contentType = response.headers.get('content-type');
    
    if (contentType && CACHEABLE_CONTENT_TYPES.includes(contentType)) {
      // Cache based on content-type, not file extension
      response.headers.set('Cache-Control', 'public, max-age=31536000, immutable');
    } else {
      // Don't cache unknown content types
      response.headers.set('Cache-Control', 'no-store');
    }
    
    return response;
  }
  
  // Default response for other paths
  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  return response;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
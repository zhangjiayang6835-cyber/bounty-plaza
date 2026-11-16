from typing import Dict, Any

def preserve_forwarded_host(scope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures RFC 7239 Forwarded header info is preserved in the ASGI scope
    even when the application is sub-mounted.
    """
    headers = dict(scope.get("headers", []))
    forwarded = headers.get(b"forwarded", b"").decode("latin-1")
    
    if forwarded:
        # Parse RFC 7239 Forwarded header
        # Format: Forwarded: for=192.0.2.60;proto=http;by=203.0.113.43
        params = dict(item.split("=", 1) for item in forwarded.split(";") if "=" in item)
        
        if "host" in params:
            # Update scope to reflect the original host authority
            scope["client_host"] = params["host"]
            # Ensure the original host is passed down to sub-apps
            scope["headers"] = [
                (k, v) for k, v in scope.get("headers", []) 
                if k.lower() != b"host"
            ] + [(b"host", params["host"].encode("latin-1"))]
            
    return scope

To solve the issue, we'll create a middleware that normalizes the `Forwarded` header before adjusting the scope. This ensures the outer host is preserved.

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class PreserveForwardedHostMiddleware(BaseHTTPMiddleware):
    def __call__(self, request: Request, call_next) -> Response:
        scope = request.scope.copy()
        # Normalize the Forwarded header
        normalize_forwarded_headers(scope)
        path = scope.get("path", "")
        root_path = scope.get("root_path", "")
        return Response(
            call_next(Request(scope_for(path, root_path)))
        )
```

This middleware ensures the `Forwarded` header is properly normalized before the scope is adjusted, preserving the outer host authority.
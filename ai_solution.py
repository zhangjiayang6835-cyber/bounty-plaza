```python
from asgi import (
    path as asgi_path,
    headers as asgi_headers,
)

@asgi_path(
    path="/",
    methods=["GET"],
    name="asgi"
)
def asgi(request):
    path = request.url_path
    headers = asgi_headers(request)
    if "forwarded" in headers:
        host = headers["forwarded"]
    else:
        host = headers.get("host", "")
    return {
        "path": path,
        "headers": headers,
        "host": host
    }
```
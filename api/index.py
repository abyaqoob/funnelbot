"""Vercel serverless entrypoint for FunnelBot with path restoration."""
import os
import sys
from urllib.parse import urlsplit

# Ensure project root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app as _fastapi_app


class VercelPathNormalizer:
    """
    ASGI middleware ensuring Vercel internal rewrites route to the original requested path
    (from x-forwarded-url, x-matched-path, etc.) rather than Vercel's internal function path '/api/index.py'.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))

            # 1. Inspect headers set by Vercel's edge proxy for the original request URL
            normalized = False
            for header_name in (
                b"x-forwarded-url",
                b"x-forwarded-uri",
                b"x-original-url",
                b"x-matched-path",
                b"x-invoke-path",
            ):
                raw = headers.get(header_name)
                if raw:
                    path = urlsplit(raw.decode("latin1", errors="ignore")).path
                    if path and path not in ("/api/index.py", "/api/index"):
                        scope["path"] = path
                        normalized = True
                        break

            # 2. Fallback: if path is still /api/index.py or starts with /api/index.py, strip prefix
            if not normalized:
                path = scope.get("path", "")
                for prefix in ("/api/index.py", "/api/index"):
                    if path == prefix:
                        scope["path"] = "/"
                        break
                    elif path.startswith(prefix + "/"):
                        scope["path"] = path[len(prefix) :] or "/"
                        break

        await self.asgi_app(scope, receive, send)


# Export the wrapped ASGI application for Vercel serverless runtime
app = VercelPathNormalizer(_fastapi_app)

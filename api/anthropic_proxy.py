"""
Anthropic API Proxy
===================
Transparent reverse-proxy that forwards every request arriving at
    /api/anthropic/<path>
to
    https://api.anthropic.com/<path>

and streams the response back to the caller, including status codes and
headers, so that any Anthropic SDK or curl command can simply point its
base-URL at https://themanhattanproject.ai/api/anthropic and work exactly as
if it were talking directly to api.anthropic.com.

The caller supplies everything: their own API key (x-api-key or
Authorization: Bearer), anthropic-version / anthropic-beta headers, and the
request body (model, messages, max_tokens, stream, ...). Nothing is stored.

Supports:
  - Regular (non-streaming) JSON responses
  - Server-Sent Events (SSE) streaming responses
  - All HTTP methods (POST, GET, DELETE, etc.) and query strings
  - CORS preflight, so browser clients can call it directly
"""

import requests as http_requests
from flask import Blueprint, request, Response, stream_with_context
import logging

logger = logging.getLogger(__name__)

ANTHROPIC_BASE_URL = "https://api.anthropic.com"

anthropic_proxy_bp = Blueprint("anthropic_proxy", __name__)

# ─── Headers we must NOT copy from the upstream response ─────────────
# (Flask / the WSGI layer sets these itself based on the actual response)
HOP_BY_HOP_HEADERS = frozenset({
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
    "set-cookie",
})

# ─── Headers we must NOT forward from the client to Anthropic ────────
STRIP_REQUEST_HEADERS = frozenset({
    "host",
    "content-length",    # requests recalculates this
    "accept-encoding",   # let requests negotiate an encoding it can decode
    "cookie",            # never leak our site's session cookies upstream
    "connection",
    "keep-alive",
    "te",
    "upgrade",
    "proxy-authorization",
    "origin",
    "referer",
})

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Expose-Headers": "*",
    "Access-Control-Max-Age": "86400",
}


def _build_upstream_url(path: str) -> str:
    """Construct the full Anthropic API URL from the sub-path."""
    return f"{ANTHROPIC_BASE_URL}/{path.lstrip('/')}"


def _filtered_request_headers() -> dict:
    """
    Return the incoming request headers minus the ones we should not
    forward (Host, Cookie, X-Forwarded-*, etc.).
    """
    return {
        key: value
        for key, value in request.headers
        if key.lower() not in STRIP_REQUEST_HEADERS
        and not key.lower().startswith(("x-forwarded-", "x-real-ip", "cf-", "x-vercel-", "x-render-"))
    }


def _filtered_response_headers(upstream_headers) -> list[tuple[str, str]]:
    """
    Return upstream response headers minus hop-by-hop / encoding headers
    that the WSGI layer should set itself, plus permissive CORS headers.
    """
    headers = [
        (key, value)
        for key, value in upstream_headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and not key.lower().startswith("access-control-")
    ]
    headers.extend(CORS_HEADERS.items())
    return headers


def _proxy_error(message: str, status: int):
    """Error body shaped like Anthropic's, so SDKs surface it cleanly."""
    return {"type": "error", "error": {"type": "proxy_error", "message": message}}, status, CORS_HEADERS


@anthropic_proxy_bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy(path: str):
    """
    Catch-all proxy handler.

    1. Rebuilds the upstream URL from the sub-path.
    2. Copies the client's method, headers, query-string, and body.
    3. Streams the Anthropic response back to the caller.
    """
    if request.method == "OPTIONS":
        return "", 204, CORS_HEADERS

    upstream_url = _build_upstream_url(path)
    headers = _filtered_request_headers()

    logger.info("[ANTHROPIC-PROXY] %s %s → %s", request.method, request.path, upstream_url)

    try:
        # Forward the request, streaming the response so SSE works
        upstream_resp = http_requests.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            params=request.args.items(multi=True),  # forward query-string as-is
            data=request.get_data(),                # forward raw body as-is
            stream=True,                            # stream for SSE support
            allow_redirects=False,
            timeout=(10, 600),                      # 10s connect, 10min between bytes
        )
    except http_requests.exceptions.Timeout:
        logger.error("[ANTHROPIC-PROXY] Timeout connecting to %s", upstream_url)
        return _proxy_error("Upstream timeout connecting to Anthropic API", 504)
    except http_requests.exceptions.ConnectionError:
        logger.error("[ANTHROPIC-PROXY] Connection error to %s", upstream_url)
        return _proxy_error("Could not connect to Anthropic API", 502)
    except Exception as e:
        logger.exception("[ANTHROPIC-PROXY] Unexpected error proxying to %s", upstream_url)
        return _proxy_error(str(e), 500)

    resp_headers = _filtered_response_headers(upstream_resp.headers)
    is_sse = upstream_resp.headers.get("Content-Type", "").startswith("text/event-stream")
    if is_sse:
        # Stop nginx-style buffering layers from holding SSE events back
        resp_headers.append(("X-Accel-Buffering", "no"))

    def generate():
        """Yield upstream chunks to the client as soon as they arrive."""
        try:
            # chunk_size=None yields data as it arrives (decoded if gzipped)
            for chunk in upstream_resp.iter_content(chunk_size=None if is_sse else 8192):
                if chunk:
                    yield chunk
        finally:
            upstream_resp.close()

    return Response(
        stream_with_context(generate()),
        status=upstream_resp.status_code,
        headers=resp_headers,
    )

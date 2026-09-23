"""
Anthropic API Proxy
===================
Transparent reverse-proxy that forwards every request arriving at
    /api/anthropic/<path>
to
    https://api.anthropic.com/<path>

and streams the response back to the caller byte-for-byte, including
all headers and status codes, so that any Anthropic SDK or curl command
can simply point its base-URL at themanhattanproject.ai/api/anthropic
and work exactly as if it were talking directly to api.anthropic.com.

Supports:
  - Regular (non-streaming) JSON responses
  - Server-Sent Events (SSE) streaming responses
  - All HTTP methods (POST, GET, DELETE, etc.)
  - Full header passthrough (auth, anthropic-version, beta headers, etc.)
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
})

# ─── Headers we must NOT forward from the client to Anthropic ────────
STRIP_REQUEST_HEADERS = frozenset({
    "host",
    "content-length",    # requests recalculates this
})


def _build_upstream_url(path: str) -> str:
    """Construct the full Anthropic API URL from the sub-path."""
    return f"{ANTHROPIC_BASE_URL}/{path}"


def _filtered_request_headers() -> dict:
    """
    Return the incoming request headers minus the ones we should not
    forward (Host, Content-Length, etc.).
    """
    return {
        key: value
        for key, value in request.headers
        if key.lower() not in STRIP_REQUEST_HEADERS
    }


def _filtered_response_headers(upstream_headers) -> list[tuple[str, str]]:
    """
    Return upstream response headers minus hop-by-hop / encoding headers
    that the WSGI layer should set itself.
    """
    return [
        (key, value)
        for key, value in upstream_headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    ]


@anthropic_proxy_bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy(path: str):
    """
    Catch-all proxy handler.

    1. Rebuilds the upstream URL from the sub-path.
    2. Copies the client's method, headers, query-string, and body.
    3. Streams the Anthropic response back to the caller.
    """
    upstream_url = _build_upstream_url(path)
    headers = _filtered_request_headers()

    logger.info("[ANTHROPIC-PROXY] %s %s → %s", request.method, request.path, upstream_url)

    try:
        # Forward the request, streaming the response so SSE works
        upstream_resp = http_requests.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            params=request.args,          # forward query-string as-is
            data=request.get_data(),       # forward raw body as-is
            stream=True,                   # stream for SSE support
            timeout=(10, 300),             # 10s connect, 5min read
        )

        # Build the list of response headers to pass back
        resp_headers = _filtered_response_headers(upstream_resp.headers)

        def generate():
            """Yield upstream chunks to the client."""
            try:
                for chunk in upstream_resp.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            finally:
                upstream_resp.close()

        return Response(
            stream_with_context(generate()),
            status=upstream_resp.status_code,
            headers=resp_headers,
            content_type=upstream_resp.headers.get("Content-Type", "application/json"),
        )

    except http_requests.exceptions.Timeout:
        logger.error("[ANTHROPIC-PROXY] Timeout connecting to %s", upstream_url)
        return {"error": {"type": "proxy_error", "message": "Upstream timeout connecting to Anthropic API"}}, 504

    except http_requests.exceptions.ConnectionError:
        logger.error("[ANTHROPIC-PROXY] Connection error to %s", upstream_url)
        return {"error": {"type": "proxy_error", "message": "Could not connect to Anthropic API"}}, 502

    except Exception as e:
        logger.exception("[ANTHROPIC-PROXY] Unexpected error proxying to %s", upstream_url)
        return {"error": {"type": "proxy_error", "message": str(e)}}, 500

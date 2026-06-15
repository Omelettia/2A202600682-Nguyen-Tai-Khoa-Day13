from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear contextvars to avoid leakage between requests.
        clear_contextvars()

        # Reuse an incoming x-request-id (propagated from upstream) or mint a new
        # one in the format req-<8-char-hex>.
        incoming = request.headers.get("x-request-id")
        correlation_id = incoming or f"req-{uuid.uuid4().hex[:8]}"

        # Bind the correlation_id so every log emitted during this request carries it.
        bind_contextvars(correlation_id=correlation_id)

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Expose the correlation_id and processing time to the caller.
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.2f}"

        return response

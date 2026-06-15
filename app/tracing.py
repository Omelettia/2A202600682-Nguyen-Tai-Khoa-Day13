from __future__ import annotations

import os
from typing import Any

try:
    # Langfuse Python SDK v3: the @observe decorator and the singleton client come
    # straight off the top-level package. (v2's `langfuse.decorators` module was
    # removed in v3 — importing it here is what used to silently disable tracing.)
    from langfuse import get_client, observe
except Exception:  # pragma: no cover - keeps the lab runnable before langfuse is set up
    def observe(func: Any = None, **_kwargs: Any):
        """No-op stand-in for langfuse's @observe when the SDK is unavailable."""

        def decorator(fn):
            return fn

        return decorator(func) if callable(func) else decorator

    class _DummySpan:
        def update(self, **_kwargs: Any) -> "_DummySpan":
            return self

        def __enter__(self) -> "_DummySpan":
            return self

        def __exit__(self, *_args: Any) -> bool:
            return False

    class _DummyClient:
        def update_current_trace(self, **_kwargs: Any) -> None:
            return None

        def update_current_span(self, **_kwargs: Any) -> None:
            return None

        def update_current_generation(self, **_kwargs: Any) -> None:
            return None

        def start_as_current_span(self, **_kwargs: Any) -> "_DummySpan":
            return _DummySpan()

        def start_as_current_generation(self, **_kwargs: Any) -> "_DummySpan":
            return _DummySpan()

    def get_client(*_args: Any, **_kwargs: Any) -> "_DummyClient":
        return _DummyClient()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

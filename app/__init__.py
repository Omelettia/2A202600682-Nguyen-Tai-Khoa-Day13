from __future__ import annotations

# Load .env as early as possible so every submodule (tracing, logging_config, ...)
# sees LANGFUSE_* keys, LOG_PATH, etc. uvicorn does not auto-load .env, so this is
# the single place that guarantees it for any entry point that imports the package.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass

__all__: list[str] = []

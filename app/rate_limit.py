"""slowapi limiter — per-tier rate-limit buckets.

The Regenold route uses a callable ``limit_value`` that resolves the
limit string from the bucket key (60/min for ``regenold-key:`` buckets,
30/min for ``regenold-anon:`` buckets). See ``app/routes/regenold.py``.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit.storage_uri,
    default_limits=[settings.rate_limit.default_limit],
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "code": "rate_limited",
            "message": f"Rate limit exceeded: {exc.detail}",
        },
    )

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.utils.exceptions import RateLimitError

_rate_buckets: dict[str, list[datetime]] = defaultdict(list)


async def rate_limit_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/analyze"):
        return await call_next(request)

    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=1)
    bucket = _rate_buckets[client_ip]
    _rate_buckets[client_ip] = [t for t in bucket if t > window_start]

    if len(_rate_buckets[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        exc = RateLimitError()
        return JSONResponse(status_code=429, content={"code": exc.code, "message": exc.message})

    _rate_buckets[client_ip].append(now)
    return await call_next(request)

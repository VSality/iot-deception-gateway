import time
from collections import defaultdict

# Process-local state; resets on restart; not shared across uvicorn workers.
_request_timestamps: defaultdict[str, list[float]] = defaultdict(list)

MAX_REQUESTS = 10
WINDOW_SECONDS = 1.0


def check_rate_limit(client_ip: str) -> bool:
    now = time.monotonic()
    timestamps = _request_timestamps[client_ip]
    timestamps.append(now)

    cutoff = now - WINDOW_SECONDS
    _request_timestamps[client_ip] = [ts for ts in timestamps if ts >= cutoff]

    return len(_request_timestamps[client_ip]) > MAX_REQUESTS

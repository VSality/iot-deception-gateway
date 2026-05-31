import time
from typing import Literal

MAX_FAILURES = 3
WINDOW_SECONDS = 60

_failures_by_client: dict[str, list[float]] = {}

LoginFailureOutcome = Literal["retry", "trigger_ban"]


def _prune_old(timestamps: list[float], now: float) -> list[float]:
    cutoff = now - WINDOW_SECONDS
    return [t for t in timestamps if t >= cutoff]


def record_failed_login(client_key: str) -> LoginFailureOutcome:
    if not client_key:
        return "retry"
    now = time.monotonic()
    history = _prune_old(_failures_by_client.get(client_key, []), now)
    history.append(now)
    _failures_by_client[client_key] = history
    if len(history) >= MAX_FAILURES:
        return "trigger_ban"
    return "retry"


def check_brute_force(client_ip: str, path: str) -> bool:
    # Login brute-force is handled explicitly via record_failed_login from /api/auth/login.
    return False

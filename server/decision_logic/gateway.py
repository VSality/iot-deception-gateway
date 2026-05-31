import asyncio

from fastapi import Request

from decision_logic.client_identity import client_display_label, client_key

# Sandbox / real session by client fingerprint (IP + X-Gateway-Client-Id).
BLACKLIST_CLIENTS: set[str] = set()
WHITELIST_CLIENTS: set[str] = set()
REAL_SESSION_CLIENTS: set[str] = set()


async def is_attacker(request: Request) -> bool:
    key = client_key(request)
    if key in BLACKLIST_CLIENTS:
        return True
    if key in WHITELIST_CLIENTS:
        return False
    return False


async def _broadcast_ip_state() -> None:
    from utils.ws_events import ip_state_event
    from ws.dashboard import manager

    await manager.broadcast_json(ip_state_event())


def _schedule_ip_state_broadcast() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_broadcast_ip_state())


def record_real_session(request: Request) -> None:
    key = client_key(request)
    if not key or key in BLACKLIST_CLIENTS:
        return
    if key in REAL_SESSION_CLIENTS:
        return
    REAL_SESSION_CLIENTS.add(key)
    _schedule_ip_state_broadcast()


def ban_client(request: Request) -> None:
    key = client_key(request)
    if not key:
        return
    WHITELIST_CLIENTS.discard(key)
    REAL_SESSION_CLIENTS.discard(key)
    BLACKLIST_CLIENTS.add(key)
    _schedule_ip_state_broadcast()


def ban_client_key(key: str) -> None:
    if not key:
        return
    WHITELIST_CLIENTS.discard(key)
    REAL_SESSION_CLIENTS.discard(key)
    BLACKLIST_CLIENTS.add(key)
    _schedule_ip_state_broadcast()


def whitelist_client_key(key: str, *, schedule_ip_state: bool = True) -> str:
    """Whitelist fingerprint. Returns display label."""
    if not key:
        return ""
    BLACKLIST_CLIENTS.discard(key)
    WHITELIST_CLIENTS.add(key)
    REAL_SESSION_CLIENTS.add(key)
    if schedule_ip_state:
        _schedule_ip_state_broadcast()
    return client_display_label(key)


def whitelist_client(request: Request) -> None:
    whitelist_client_key(client_key(request))


def sorted_client_labels(keys: set[str]) -> list[str]:
    return sorted(client_display_label(k) for k in keys)

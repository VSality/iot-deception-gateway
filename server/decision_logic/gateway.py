from fastapi import Request

# Shared mutable blacklist; detection engine adds IPs at runtime.
BLACKLIST_IPS: set[str] = set()
WHITELIST_IPS: set[str] = set()


async def is_attacker(request: Request) -> bool:
    host = request.client.host if request.client else ""
    if host in WHITELIST_IPS:
        return False
    return host in BLACKLIST_IPS


def whitelist_ip(client_ip: str) -> None:
    if not client_ip:
        return
    BLACKLIST_IPS.discard(client_ip)
    WHITELIST_IPS.add(client_ip)

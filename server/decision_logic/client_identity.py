from fastapi import Request

GATEWAY_CLIENT_ID_HEADER = "x-gateway-client-id"
ANONYMOUS_CLIENT_ID = "_anonymous"


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def get_gateway_client_id(request: Request) -> str | None:
    raw = request.headers.get(GATEWAY_CLIENT_ID_HEADER)
    if raw and raw.strip():
        return raw.strip()[:64]
    q = request.query_params.get("client_id")
    if q and q.strip():
        return q.strip()[:64]
    return None


def client_key(request: Request) -> str:
    ip = get_client_ip(request)
    cid = get_gateway_client_id(request) or ANONYMOUS_CLIENT_ID
    return f"{ip}|{cid}"


def client_display_label(key: str) -> str:
    if "|" not in key:
        return key
    ip, cid = key.split("|", 1)
    if cid == ANONYMOUS_CLIENT_ID:
        return f"{ip} · no client id"
    short = cid[:8] if len(cid) > 8 else cid
    return f"{ip} · {short}"

"""Static decoy responses for sandboxed clients (no real exploit execution)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecoyResponse:
    status_code: int
    media_type: str
    body: str


# Longest-prefix match first (more specific paths above generic ones).
_DECOY_BY_PREFIX: list[tuple[str, DecoyResponse]] = [
    (
        "/clip/v2/resource",
        DecoyResponse(
            403,
            "application/json",
            '{"errors":[{"description":"invalid/missing token in request"}]}',
        ),
    ),
    (
        "/api/tags",
        DecoyResponse(
            403,
            "application/json",
            '{"errors":[{"description":"unauthorized user"}]}',
        ),
    ),
    (
        "/device.xml",
        DecoyResponse(
            500,
            "application/xml",
            '<?xml version="1.0"?><error><code>DEVICE_BUSY</code></error>',
        ),
    ),
    (
        "/goform/",
        DecoyResponse(
            500,
            "text/html",
            "<html><body>Internal Server Error</body></html>",
        ),
    ),
    (
        "/ota/",
        DecoyResponse(
            400,
            "application/json",
            '{"status":"error","message":"OTA session expired"}',
        ),
    ),
    (
        "/api/legacy/auth",
        DecoyResponse(
            401,
            "application/json",
            '{"authenticated":false,"reason":"invalid credentials"}',
        ),
    ),
    (
        "/debug/",
        DecoyResponse(
            403,
            "application/json",
            '{"error":"debug interface disabled"}',
        ),
    ),
]


def match_decoy(path: str) -> DecoyResponse | None:
    path_lower = path.lower()
    for prefix, decoy in _DECOY_BY_PREFIX:
        if path_lower.startswith(prefix.lower()):
            return decoy
    return None

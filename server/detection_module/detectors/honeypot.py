# Typical scanner / probe paths (substring match, case-insensitive).
_HONEYPOT_PATTERNS = (
    "/wp-admin",
    "/api/admin",
    "/phpmyadmin",
    "/.env",
)


def check_honeypot_path(path: str) -> bool:
    path_lower = path.lower()
    return any(pattern in path_lower for pattern in _HONEYPOT_PATTERNS)

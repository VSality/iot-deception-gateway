from fastapi import Request

from decision_logic.client_identity import client_display_label, client_key, get_client_ip
from decision_logic.device_catalog import CLIMATE_DEVICE_ID, set_climate_alert_active
from decision_logic.gateway import ban_client, ban_client_key
from detection_module.detectors.brute_force import check_brute_force, record_failed_login
from detection_module.detectors.honeypot import check_honeypot_path
from detection_module.detectors.port_scan import check_port_scan
from detection_module.detectors.rate_limit import check_rate_limit
from utils.ws_notify import broadcast_attack_alert, schedule_device_state

DETECTOR_IDS = frozenset({"honeypot", "ratelimit", "bruteforce", "portscan"})


async def emit_detection_hit(
    detector_id: str,
    message: str,
    request: Request | None = None,
    *,
    client_ip: str = "",
) -> None:
    if detector_id not in DETECTOR_IDS:
        raise ValueError(f"Unknown detector: {detector_id}")

    if request is not None:
        key = client_key(request)
        ip = get_client_ip(request)
        alert_ip = ip
    else:
        ip = client_ip
        key = f"{ip}|_anonymous" if ip else ""
        alert_ip = ip

    await broadcast_attack_alert(detector_id, message, alert_ip)
    if request is not None:
        ban_client(request)
    elif key:
        ban_client_key(key)

    label = client_display_label(key) if key else ip
    detail = f"Client {label} blocked by {detector_id} — {message}"
    print(f"[DETECTION] {detail}")
    set_climate_alert_active(True)
    schedule_device_state(CLIMATE_DEVICE_ID, "alert", "sensor")


async def process_failed_ha_login(request: Request) -> None:
    key = client_key(request)
    outcome = record_failed_login(key)
    if outcome == "trigger_ban":
        await emit_detection_hit(
            "bruteforce",
            "Brute force detected. IP routed to Shadow World.",
            request,
        )


def _honeypot_alert_message(path: str) -> str:
    path_lower = path.lower()
    if "/api/debug" in path_lower or "/.env" in path_lower:
        return "Fuzzing detected. IP silently isolated."
    return f"Honeypot path probe: {path}"


async def monitor_traffic(request: Request) -> None:
    """Run all detectors; on threat, alert dashboard and ban client fingerprint."""
    client_ip = get_client_ip(request)
    path = request.url.path

    checks: list[tuple[str, bool, str]] = [
        (
            "honeypot",
            check_honeypot_path(path),
            _honeypot_alert_message(path),
        ),
        (
            "ratelimit",
            check_rate_limit(client_ip),
            "Rate limit exceeded (>10 req/s)",
        ),
        (
            "bruteforce",
            check_brute_force(client_ip, path),
            "Brute-force login attempts",
        ),
        (
            "portscan",
            check_port_scan(client_ip),
            "Port scan activity detected",
        ),
    ]

    for detector_id, triggered, message in checks:
        if triggered:
            await emit_detection_hit(detector_id, message, request)
            break

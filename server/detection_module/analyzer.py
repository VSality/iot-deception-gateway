from fastapi import Request

from decision_logic.gateway import BLACKLIST_IPS
from detection_module.detectors.brute_force import check_brute_force
from detection_module.detectors.honeypot import check_honeypot_path
from detection_module.detectors.port_scan import check_port_scan
from detection_module.detectors.rate_limit import check_rate_limit


async def monitor_traffic(request: Request) -> None:
    """Run all detectors; on threat, add client IP to shared blacklist."""
    client_ip = request.client.host if request.client else ""
    path = request.url.path

    checks: list[tuple[str, bool]] = [
        ("Honeypot Path", check_honeypot_path(path)),
        ("Rate Limit", check_rate_limit(client_ip)),
        ("Brute Force", check_brute_force(client_ip, path)),
        ("Port Scan", check_port_scan(client_ip)),
    ]

    for detector_name, triggered in checks:
        if triggered:
            if client_ip:
                BLACKLIST_IPS.add(client_ip)
            print(f"[DETECTION] IP {client_ip} blocked by {detector_name}")
            break

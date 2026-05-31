from datetime import datetime, timezone


def log_event(level: str, message: str) -> dict:
    return {
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def ip_state_event() -> dict:
    from decision_logic.gateway import (
        BLACKLIST_CLIENTS,
        REAL_SESSION_CLIENTS,
        sorted_client_labels,
    )

    return {
        "type": "ip_state",
        "whitelist": sorted_client_labels(REAL_SESSION_CLIENTS),
        "blacklist": sorted_client_labels(BLACKLIST_CLIENTS),
    }


def attack_alert_event(detector: str, message: str, client_ip: str = "") -> dict:
    return {
        "type": "attack_alert",
        "detector": detector,
        "message": message,
        "client_ip": client_ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def knock_progress_event(step: int) -> dict:
    return {"type": "knock_progress", "step": step}


def knock_reset_event() -> dict:
    return {"type": "knock_reset"}


def reauth_success_event(client_label: str) -> dict:
    return {
        "type": "reauth_success",
        "client": client_label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def device_state_event(
    device_id: str, state: str, device_type: str | None = None
) -> dict:
    payload: dict = {
        "type": "device_state",
        "device_id": device_id,
        "state": state,
    }
    if device_type is not None:
        payload["device_type"] = device_type
    return payload

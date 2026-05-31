from copy import deepcopy

from fastapi import APIRouter

from decision_logic.device_catalog import enrich_topology_device
from shadow_world.mirror import CANARY_LIGHT_ROOM_ID

router = APIRouter(tags=["network-topology"])

GATEWAY = {"id": "gateway", "label": "DECEPTION\nGATEWAY"}

DETECTORS = [
    {"id": "honeypot", "name": "Honeypot"},
    {"id": "ratelimit", "name": "Rate Limit"},
    {"id": "bruteforce", "name": "Brute Force"},
    {"id": "portscan", "name": "Port Scan"},
]

REAL_HUB = {"id": "real_hub", "name": "Home Assistant\n(Real)", "ip": "192.168.1.10"}
SHADOW_HUB = {"id": "shadow_hub", "name": "Home Assistant\n(Shadow)", "ip": "10.66.6.1"}

REAL_DEVICES_TOPOLOGY: list[dict] = [
    {
        "id": "dev_hue_living",
        "name": "Philips Hue — Гостиная",
        "ip": "192.168.1.21",
        "mac": "00:17:88:6F:1A:3C",
        "firmware": "1.122.2",
        "vendor": "Signify (Philips Hue)",
    },
    {
        "id": "dev_hue_kitchen",
        "name": "Philips Hue — Кухня",
        "ip": "192.168.1.22",
        "mac": "00:17:88:7B:42:E0",
        "firmware": "1.122.2",
        "vendor": "Signify (Philips Hue)",
    },
    {
        "id": "dev_lock",
        "name": "Aqara Smart Lock U100",
        "ip": "192.168.1.31",
        "mac": "54:EF:44:9A:08:D1",
        "firmware": "3.0.4",
        "vendor": "Lumi (Aqara)",
    },
    {
        "id": "dev_climate",
        "name": "Aqara Climate Sensor",
        "ip": "192.168.1.32",
        "mac": "54:EF:44:12:7F:55",
        "firmware": "1.2.8",
        "vendor": "Lumi (Aqara)",
    },
    {
        "id": "dev_camera",
        "name": "TP-Link Tapo C210",
        "ip": "192.168.1.41",
        "mac": "AC:84:C6:33:91:0A",
        "firmware": "1.3.11",
        "vendor": "TP-Link",
    },
    {
        "id": "dev_relay",
        "name": "Sonoff MINI R4",
        "ip": "192.168.1.51",
        "mac": "24:6F:28:B4:7C:E2",
        "firmware": "13.4.0",
        "vendor": "Espressif (Sonoff)",
    },
    {
        "id": "dev_voice",
        "name": "Google Nest Hub",
        "ip": "192.168.1.61",
        "mac": "1C:F2:9A:55:0D:88",
        "firmware": "1.56.328896",
        "vendor": "Google",
    },
]

_SHADOW_IP_BY_REAL_ID: dict[str, str] = {
    "dev_hue_living": "10.66.6.21",
    "dev_hue_kitchen": "10.66.6.22",
    "dev_lock": "10.66.6.31",
    "dev_climate": "10.66.6.32",
    "dev_camera": "10.66.6.41",
    "dev_relay": "10.66.6.51",
    "dev_voice": "10.66.6.61",
}

_SHADOW_FIRMWARE_BY_DEVICE_TYPE: dict[str, str] = {
    "light": "1.49.195007",
    "lock": "2.5.8-legacy",
    "sensor": "1.2.8",
}


def _build_real_devices() -> list[dict]:
    return [enrich_topology_device(deepcopy(dev), "real") for dev in REAL_DEVICES_TOPOLOGY]


def _build_shadow_devices() -> list[dict]:
    shadow: list[dict] = []
    for dev in REAL_DEVICES_TOPOLOGY:
        entry = deepcopy(dev)
        entry["id"] = f"shadow_{dev['id']}"
        entry["ip"] = _SHADOW_IP_BY_REAL_ID[dev["id"]]
        enriched = enrich_topology_device(entry, "shadow")
        enriched["firmware"] = _SHADOW_FIRMWARE_BY_DEVICE_TYPE.get(
            enriched["device_type"], "0.9.1-exposed"
        )
        if enriched["device_type"] == "light":
            enriched["vendor"] = "Signify"
        shadow.append(enriched)

    canary_raw = {
        "id": f"shadow_canary_{CANARY_LIGHT_ROOM_ID}",
        "name": f"Hall Dimmer Aux ({CANARY_LIGHT_ROOM_ID})",
        "ip": "10.66.6.99",
        "mac": "00:17:88:FF:CA:01",
        "firmware": "1.49.195007",
        "vendor": "Signify",
        "role": "canary",
    }
    shadow.append(enrich_topology_device(canary_raw, "shadow"))
    return shadow


@router.get("/api/network-topology")
async def get_network_topology() -> dict:
    return {
        "gateway": GATEWAY,
        "detectors": DETECTORS,
        "real": {"hub": REAL_HUB, "devices": _build_real_devices()},
        "shadow": {"hub": SHADOW_HUB, "devices": _build_shadow_devices()},
    }

from shadow_world.mirror import CANARY_LIGHT_ROOM_ID, REAL_DEVICES, shadow_world

CLIMATE_DEVICE_ID = "dev_climate"
CLIMATE_ALERT_ACTIVE = False

# device_type: light | lock | sensor
DEVICE_META: dict[str, dict] = {
    "dev_hue_living": {
        "device_type": "light",
        "type_label": "Light",
        "api_key": ("light", "living"),
        "default_state": "off",
    },
    "dev_hue_kitchen": {
        "device_type": "light",
        "type_label": "Light",
        "api_key": ("light", "kitchen"),
        "default_state": "off",
    },
    "dev_lock": {
        "device_type": "lock",
        "type_label": "Lock",
        "api_key": ("lock", "main_door"),
        "default_state": "locked",
    },
    "dev_climate": {
        "device_type": "sensor",
        "type_label": "Sensor",
        "default_state": "ok",
    },
    "dev_camera": {
        "device_type": "sensor",
        "type_label": "Camera",
        "default_state": "ok",
    },
    "dev_relay": {
        "device_type": "light",
        "type_label": "Relay",
        "default_state": "off",
    },
    "dev_voice": {
        "device_type": "sensor",
        "type_label": "Hub",
        "default_state": "ok",
    },
}

_LIGHT_ROOM_TO_NODE: dict[str, str] = {
    "living": "dev_hue_living",
    "kitchen": "dev_hue_kitchen",
}


def set_climate_alert_active(active: bool = True) -> None:
    global CLIMATE_ALERT_ACTIVE
    CLIMATE_ALERT_ACTIVE = active


def _base_device_id(device_id: str) -> str:
    if device_id.startswith("shadow_canary_"):
        return device_id
    return device_id.removeprefix("shadow_")


def get_device_type(device_id: str) -> str:
    base = _base_device_id(device_id)
    if base.startswith("shadow_canary_"):
        return "light"
    return DEVICE_META[base]["device_type"]


def topology_node_id_for_light(room_id: str, shadow: bool) -> str:
    base = _LIGHT_ROOM_TO_NODE[room_id]
    return f"shadow_{base}" if shadow else base


def topology_node_id_for_lock(door_id: str, shadow: bool) -> str:
    if door_id != "main_door":
        raise ValueError(f"Unknown lock: {door_id}")
    return "shadow_dev_lock" if shadow else "dev_lock"


def _read_api_state(kind: str, key: str, plane: str) -> str | None:
    store = (
        shadow_world.vulnerable_shadow_devices
        if plane == "shadow"
        else REAL_DEVICES
    )
    if kind == "light":
        light = store["lights"].get(key)
        return light["status"] if light else None
    if kind == "lock":
        lock = store["locks"].get(key)
        return lock["status"] if lock else None
    return None


def resolve_state(device_id: str, plane: str) -> str:
    if device_id.startswith("shadow_canary_"):
        light = shadow_world.vulnerable_shadow_devices["lights"].get(
            CANARY_LIGHT_ROOM_ID
        )
        return light["status"] if light else "off"

    base_id = _base_device_id(device_id)
    meta = DEVICE_META.get(base_id)
    if meta is None:
        return "ok"

    if base_id == CLIMATE_DEVICE_ID and CLIMATE_ALERT_ACTIVE and plane == "real":
        return "alert"

    api_key = meta.get("api_key")
    if api_key:
        kind, key = api_key
        state = _read_api_state(kind, key, plane)
        if state is not None:
            return state

    return meta["default_state"]


def enrich_topology_device(device: dict, plane: str) -> dict:
    device_id = device["id"]
    base_id = _base_device_id(device_id)
    if device_id.startswith("shadow_canary_"):
        enriched = {
            **device,
            "device_type": "light",
            "type_label": "Лампа",
            "state": resolve_state(device_id, plane),
        }
        return enriched

    meta = DEVICE_META[base_id]
    return {
        **device,
        "device_type": meta["device_type"],
        "type_label": meta["type_label"],
        "state": resolve_state(device_id, plane),
    }

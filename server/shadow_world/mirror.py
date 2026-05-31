from copy import deepcopy

from schemas.ha_states import devices_store_to_ha_states

# Authoritative state of the physical smart home (legal clients mutate this).
REAL_DEVICES: dict = {
    "lights": {
        "living": {
            "status": "on",
            "brightness": 100,
            "firmware": "v2.1",
            "vendor": "Philips Hue",
        },
        "kitchen": {
            "status": "off",
            "brightness": 0,
            "firmware": "v2.1",
            "vendor": "Philips Hue",
        },
    },
    "locks": {
        "main_door": {
            "status": "locked",
            "model": "Yale Smart Living",
            "battery": 90,
        },
    },
}

# Shadow-only room id; mobile app probes this to detect sandbox (not in REAL_DEVICES).
CANARY_LIGHT_ROOM_ID = "hall_dimmer_aux"

# Plausible legacy builds for shadow plane (no "vulnerable" suffix in API).
SHADOW_LIGHT_FIRMWARE = "1.49.195007"
SHADOW_LIGHT_VENDOR = "Signify"


class ShadowWorld:
    def __init__(self) -> None:
        self.vulnerable_shadow_devices = deepcopy(REAL_DEVICES)
        self._apply_deception_lens()
        self._inject_canary_light()

    def _inject_canary_light(self) -> None:
        self.vulnerable_shadow_devices["lights"][CANARY_LIGHT_ROOM_ID] = {
            "status": "off",
            "brightness": 0,
            "firmware": SHADOW_LIGHT_FIRMWARE,
            "vendor": SHADOW_LIGHT_VENDOR,
        }

    def _apply_deception_lens(self) -> None:
        for light in self.vulnerable_shadow_devices["lights"].values():
            light["firmware"] = SHADOW_LIGHT_FIRMWARE
            light["vendor"] = SHADOW_LIGHT_VENDOR

    def get_shadow_light(self, room_id: str) -> dict | None:
        light = self.vulnerable_shadow_devices["lights"].get(room_id)
        return deepcopy(light) if light is not None else None

    def toggle_shadow_light(self, room_id: str) -> str | None:
        light = self.vulnerable_shadow_devices["lights"].get(room_id)
        if light is None:
            return None
        if light["status"] == "on":
            light["status"] = "off"
            light["brightness"] = 0
        else:
            light["status"] = "on"
            light["brightness"] = 70
        return light["status"]

    def get_shadow_lock(self, door_id: str) -> dict | None:
        lock = self.vulnerable_shadow_devices["locks"].get(door_id)
        return deepcopy(lock) if lock is not None else None

    def unlock_shadow_lock(self, door_id: str) -> bool:
        lock = self.vulnerable_shadow_devices["locks"].get(door_id)
        if lock is None:
            return False
        lock["status"] = "unlocked"
        return True

    def lock_shadow_lock(self, door_id: str) -> bool:
        lock = self.vulnerable_shadow_devices["locks"].get(door_id)
        if lock is None:
            return False
        lock["status"] = "locked"
        return True

    def get_all_shadow_devices(self) -> list[dict]:
        return devices_store_to_ha_states(self.vulnerable_shadow_devices)


shadow_world = ShadowWorld()


def get_all_real_devices() -> list[dict]:
    return devices_store_to_ha_states(REAL_DEVICES)


def get_real_light(room_id: str) -> dict | None:
    light = REAL_DEVICES["lights"].get(room_id)
    return deepcopy(light) if light is not None else None


def toggle_real_light(room_id: str) -> str | None:
    light = REAL_DEVICES["lights"].get(room_id)
    if light is None:
        return None
    if light["status"] == "on":
        light["status"] = "off"
        light["brightness"] = 0
    else:
        light["status"] = "on"
        light["brightness"] = 100
    return light["status"]


def get_real_lock(door_id: str) -> dict | None:
    lock = REAL_DEVICES["locks"].get(door_id)
    return deepcopy(lock) if lock is not None else None


def unlock_real_lock(door_id: str) -> bool:
    lock = REAL_DEVICES["locks"].get(door_id)
    if lock is None:
        return False
    lock["status"] = "unlocked"
    return True


def lock_real_lock(door_id: str) -> bool:
    lock = REAL_DEVICES["locks"].get(door_id)
    if lock is None:
        return False
    lock["status"] = "locked"
    return True

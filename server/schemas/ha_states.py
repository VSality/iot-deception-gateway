from copy import deepcopy


def build_ha_state(entity_id: str, state: str, attributes: dict) -> dict:
    return {
        "entity_id": entity_id,
        "state": state,
        "attributes": deepcopy(attributes),
    }


def _friendly_name(device_key: str) -> str:
    return device_key.replace("_", " ").title()


def light_to_ha_state(room_id: str, device: dict) -> dict:
    attributes = {
        "brightness": device["brightness"],
        "firmware": device["firmware"],
        "vendor": device["vendor"],
        "friendly_name": _friendly_name(room_id),
    }
    return build_ha_state(f"light.{room_id}", device["status"], attributes)


def lock_to_ha_state(door_id: str, device: dict) -> dict:
    attributes = {
        "model": device["model"],
        "battery": device["battery"],
        "friendly_name": _friendly_name(door_id),
    }
    return build_ha_state(f"lock.{door_id}", device["status"], attributes)


def devices_store_to_ha_states(devices: dict) -> list[dict]:
    states: list[dict] = []
    for room_id, light in devices.get("lights", {}).items():
        states.append(light_to_ha_state(room_id, light))
    for door_id, lock in devices.get("locks", {}).items():
        states.append(lock_to_ha_state(door_id, lock))
    states.sort(key=lambda item: item["entity_id"])
    return states

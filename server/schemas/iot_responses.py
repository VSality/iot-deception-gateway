"""Shared JSON shapes for real and fake IoT API responses."""

SOURCE_REAL = "REAL_API"
SOURCE_SHADOW = "SHADOW_TWIN"
# Legacy alias for older docs/logs
SOURCE_FAKE = SOURCE_SHADOW


def build_light_get_response(room_id: str, device: dict, source: str) -> dict:
    return {
        "room": room_id,
        "status": device["status"],
        "brightness": device["brightness"],
        "firmware": device["firmware"],
        "vendor": device["vendor"],
        "source": source,
    }


def build_lock_get_response(door_id: str, device: dict, source: str) -> dict:
    return {
        "door": door_id,
        "status": device["status"],
        "model": device["model"],
        "battery": device["battery"],
        "source": source,
    }


def build_toggle_response(new_state: str) -> dict:
    return {"result": "success", "new_state": new_state}


def build_unlock_response() -> dict:
    return {"result": "success", "message": "Door unlocked successfully"}


def build_lock_response() -> dict:
    return {"result": "success", "message": "Door locked successfully"}

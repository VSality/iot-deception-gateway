import time
from dataclasses import dataclass

from decision_logic.gateway import whitelist_client_key
from decision_logic.port_knock_config import (
    KNOCK_LIGHT_ROOM_ID,
    KNOCK_LOCK_DOOR_ID,
    KNOCK_WINDOW_SECONDS,
)
from utils.ws_notify import (
    schedule_knock_progress,
    schedule_knock_reset,
    schedule_reauth_success,
)

# step: 1 = awaiting lock, 2 = awaiting light OFF
_progress: dict[str, "KnockProgress"] = {}


@dataclass
class KnockProgress:
    step: int
    started_at: float


def _reset(key: str, *, notify: bool = False) -> None:
    had = key in _progress
    _progress.pop(key, None)
    if notify and had:
        schedule_knock_reset()


def _expired(progress: KnockProgress) -> bool:
    return (time.time() - progress.started_at) > KNOCK_WINDOW_SECONDS


def _get_progress(key: str) -> KnockProgress | None:
    progress = _progress.get(key)
    if progress is None:
        return None
    if _expired(progress):
        _reset(key, notify=True)
        return None
    return progress


def _complete(key: str) -> bool:
    _reset(key)
    label = whitelist_client_key(key, schedule_ip_state=False)
    schedule_reauth_success(label)
    print(
        f"[PORT KNOCKING] Sequence complete. Client {label} released from sandbox."
    )
    return True


def on_shadow_light_toggle(key: str, room_id: str, new_state: str) -> bool:
    if not key:
        return False

    if room_id != KNOCK_LIGHT_ROOM_ID:
        if key in _progress:
            _reset(key, notify=True)
        return False

    progress = _get_progress(key)

    if progress is None:
        if new_state == "on":
            _progress[key] = KnockProgress(step=1, started_at=time.time())
            schedule_knock_progress(1)
        return False

    if progress.step == 1:
        _reset(key, notify=True)
        if new_state == "on":
            _progress[key] = KnockProgress(step=1, started_at=time.time())
            schedule_knock_progress(1)
        return False

    if progress.step == 2:
        if new_state == "off":
            return _complete(key)
        _reset(key, notify=True)
        return False

    return False


def on_shadow_lock_unlock(key: str, door_id: str) -> bool:
    if not key:
        return False

    if door_id != KNOCK_LOCK_DOOR_ID:
        if key in _progress:
            _reset(key, notify=True)
        return False

    progress = _get_progress(key)
    if progress is None or progress.step != 1:
        _reset(key, notify=True)
        return False

    progress.step = 2
    schedule_knock_progress(2)
    return False

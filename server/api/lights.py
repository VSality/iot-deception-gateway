import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request

from decision_logic.gateway import is_attacker, whitelist_ip
from decision_logic.port_knock_config import (
    KNOCK_REQUIRED_TOGGLES,
    KNOCK_WINDOW_SECONDS,
    PORT_KNOCK_ROOM_ID,
)
from schemas.iot_responses import (
    SOURCE_REAL,
    SOURCE_SHADOW,
    build_light_get_response,
    build_toggle_response,
)
from shadow_world.jitter import apply_shadow_jitter
from shadow_world.mirror import (
    get_real_light,
    shadow_world,
    toggle_real_light,
)

router = APIRouter(tags=["iot-lights"])

# In-band port knocking: timestamps of shadow toggles per client IP (process-local).
knock_tracker: defaultdict[str, list[float]] = defaultdict(list)


def _record_port_knock(client_ip: str, room_id: str) -> None:
    """IoT Port Knocking — secret toggle pattern releases falsely blocked users."""
    if room_id != PORT_KNOCK_ROOM_ID:
        return

    now = time.time()
    history = knock_tracker[client_ip]
    history.append(now)
    cutoff = now - KNOCK_WINDOW_SECONDS
    knock_tracker[client_ip] = [ts for ts in history if ts >= cutoff]

    if len(knock_tracker[client_ip]) >= KNOCK_REQUIRED_TOGGLES:
        whitelist_ip(client_ip)
        knock_tracker[client_ip].clear()
        print(
            f"[PORT KNOCKING] Secret pattern detected! IP {client_ip} released from sandbox."
        )


@router.get("/api/lights/{room_id}")
async def get_light(
    room_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        device = shadow_world.get_shadow_light(room_id)
        if device is None:
            raise HTTPException(
                status_code=404, detail=f"Light room '{room_id}' not found"
            )
        print(f"[SHADOW] GET light '{room_id}' for attacker")
        return build_light_get_response(room_id, device, SOURCE_SHADOW)

    device = get_real_light(room_id)
    if device is None:
        raise HTTPException(
            status_code=404, detail=f"Light room '{room_id}' not found"
        )
    print(f"[REAL] GET light '{room_id}'")
    return build_light_get_response(room_id, device, SOURCE_REAL)


@router.post("/api/lights/{room_id}/toggle")
async def toggle_light(
    request: Request,
    room_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    client_ip = request.client.host if request.client else ""

    if attacker:
        if client_ip:
            _record_port_knock(client_ip, room_id)

        await apply_shadow_jitter()
        new_state = shadow_world.toggle_shadow_light(room_id)
        if new_state is None:
            raise HTTPException(
                status_code=404, detail=f"Light room '{room_id}' not found"
            )
        print(
            f"[SHADOW] Attacker toggled shadow light '{room_id}' to {new_state.upper()}"
        )
        return build_toggle_response(new_state)

    new_state = toggle_real_light(room_id)
    if new_state is None:
        raise HTTPException(
            status_code=404, detail=f"Light room '{room_id}' not found"
        )
    print(f"[REAL] Toggled light '{room_id}' to {new_state.upper()}")
    return build_toggle_response(new_state)

from fastapi import APIRouter, Depends, HTTPException, Request

from decision_logic.client_identity import client_key
from decision_logic.device_catalog import topology_node_id_for_light
from decision_logic.gateway import is_attacker, record_real_session
from decision_logic.port_knock_fsm import on_shadow_light_toggle
from utils.ws_notify import schedule_device_state
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


@router.get("/api/lights/{room_id}")
async def get_light(
    request: Request,
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
    record_real_session(request)
    print(f"[REAL] GET light '{room_id}'")
    return build_light_get_response(room_id, device, SOURCE_REAL)


@router.post("/api/lights/{room_id}/toggle")
async def toggle_light(
    request: Request,
    room_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        new_state = shadow_world.toggle_shadow_light(room_id)
        if new_state is None:
            raise HTTPException(
                status_code=404, detail=f"Light room '{room_id}' not found"
            )
        on_shadow_light_toggle(client_key(request), room_id, new_state)
        print(
            f"[SHADOW] Attacker toggled shadow light '{room_id}' to {new_state.upper()}"
        )
        try:
            node_id = topology_node_id_for_light(room_id, shadow=True)
            schedule_device_state(node_id, new_state, "light")
        except KeyError:
            pass
        return build_toggle_response(new_state)

    new_state = toggle_real_light(room_id)
    if new_state is None:
        raise HTTPException(
            status_code=404, detail=f"Light room '{room_id}' not found"
        )
    record_real_session(request)
    print(f"[REAL] Toggled light '{room_id}' to {new_state.upper()}")
    try:
        node_id = topology_node_id_for_light(room_id, shadow=False)
        schedule_device_state(node_id, new_state, "light")
    except KeyError:
        pass
    return build_toggle_response(new_state)

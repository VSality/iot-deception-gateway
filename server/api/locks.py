from fastapi import APIRouter, Depends, HTTPException, Request

from decision_logic.client_identity import client_key
from decision_logic.device_catalog import topology_node_id_for_lock
from decision_logic.gateway import is_attacker, record_real_session
from decision_logic.port_knock_fsm import on_shadow_lock_unlock
from utils.ws_notify import schedule_device_state
from schemas.iot_responses import (
    SOURCE_REAL,
    SOURCE_SHADOW,
    build_lock_get_response,
    build_lock_response,
    build_unlock_response,
)
from shadow_world.jitter import apply_shadow_jitter
from shadow_world.mirror import (
    get_real_lock,
    lock_real_lock,
    shadow_world,
    unlock_real_lock,
)

router = APIRouter(tags=["iot-locks"])


@router.get("/api/locks/{door_id}")
async def get_lock(
    request: Request,
    door_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        device = shadow_world.get_shadow_lock(door_id)
        if device is None:
            raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
        print(f"[SHADOW] GET lock '{door_id}' for attacker")
        return build_lock_get_response(door_id, device, SOURCE_SHADOW)

    device = get_real_lock(door_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
    record_real_session(request)
    print(f"[REAL] GET lock '{door_id}'")
    return build_lock_get_response(door_id, device, SOURCE_REAL)


@router.post("/api/locks/{door_id}/unlock")
async def unlock_lock(
    request: Request,
    door_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        if not shadow_world.unlock_shadow_lock(door_id):
            raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
        on_shadow_lock_unlock(client_key(request), door_id)
        print(f"[SHADOW] Attacker unlocked shadow lock '{door_id}'")
        try:
            node_id = topology_node_id_for_lock(door_id, shadow=True)
            schedule_device_state(node_id, "unlocked", "lock")
        except ValueError:
            pass
        return build_unlock_response()

    if not unlock_real_lock(door_id):
        raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
    record_real_session(request)
    print(f"[REAL] Unlocked lock '{door_id}'")
    try:
        node_id = topology_node_id_for_lock(door_id, shadow=False)
        schedule_device_state(node_id, "unlocked", "lock")
    except ValueError:
        pass
    return build_unlock_response()


@router.post("/api/locks/{door_id}/lock")
async def lock_lock(
    request: Request,
    door_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        if not shadow_world.lock_shadow_lock(door_id):
            raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
        print(f"[SHADOW] Attacker locked shadow lock '{door_id}'")
        try:
            node_id = topology_node_id_for_lock(door_id, shadow=True)
            schedule_device_state(node_id, "locked", "lock")
        except ValueError:
            pass
        return build_lock_response()

    if not lock_real_lock(door_id):
        raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
    record_real_session(request)
    print(f"[REAL] Locked lock '{door_id}'")
    try:
        node_id = topology_node_id_for_lock(door_id, shadow=False)
        schedule_device_state(node_id, "locked", "lock")
    except ValueError:
        pass
    return build_lock_response()

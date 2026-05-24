from fastapi import APIRouter, Depends, HTTPException

from decision_logic.gateway import is_attacker
from schemas.iot_responses import (
    SOURCE_REAL,
    SOURCE_SHADOW,
    build_lock_get_response,
    build_unlock_response,
)
from shadow_world.jitter import apply_shadow_jitter
from shadow_world.mirror import (
    get_real_lock,
    shadow_world,
    unlock_real_lock,
)

router = APIRouter(tags=["iot-locks"])


@router.get("/api/locks/{door_id}")
async def get_lock(
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
    print(f"[REAL] GET lock '{door_id}'")
    return build_lock_get_response(door_id, device, SOURCE_REAL)


@router.post("/api/locks/{door_id}/unlock")
async def unlock_lock(
    door_id: str,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if attacker:
        await apply_shadow_jitter()
        if not shadow_world.unlock_shadow_lock(door_id):
            raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
        print(f"[SHADOW] Attacker unlocked shadow lock '{door_id}'")
        return build_unlock_response()

    if not unlock_real_lock(door_id):
        raise HTTPException(status_code=404, detail=f"Lock '{door_id}' not found")
    print(f"[REAL] Unlocked lock '{door_id}'")
    return build_unlock_response()

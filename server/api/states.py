from fastapi import APIRouter, Depends, Request

from decision_logic.gateway import is_attacker, record_real_session
from shadow_world.jitter import apply_states_jitter
from shadow_world.mirror import get_all_real_devices, shadow_world

router = APIRouter(tags=["home-assistant-states"])


@router.get("/api/states")
async def get_states(
    request: Request,
    attacker: bool = Depends(is_attacker),
) -> list[dict]:
    print(f"[API] Client requested global states. Defending: {attacker}.")
    if attacker:
        await apply_states_jitter()
        return shadow_world.get_all_shadow_devices()
    record_real_session(request)
    return get_all_real_devices()

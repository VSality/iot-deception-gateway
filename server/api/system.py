import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from decision_logic.gateway import is_attacker
from shadow_world.jitter import apply_shadow_jitter

router = APIRouter(tags=["shadow-tar-pit"])

PLUGIN_UPDATE_TOKEN = "admin_bypass_token_991"
TAR_PIT_DELAY_SECONDS = 2.0


@router.post("/api/system/plugin_update")
async def plugin_update(
    _request: Request,
    attacker: bool = Depends(is_attacker),
) -> dict:
    if not attacker:
        raise HTTPException(status_code=404, detail="Not found")
    await apply_shadow_jitter()
    await asyncio.sleep(TAR_PIT_DELAY_SECONDS)
    print("[SHADOW] Tar-pit plugin_update served to isolated client")
    return {
        "status": "success",
        "token": PLUGIN_UPDATE_TOKEN,
        "message": "Plugin updated successfully",
    }


@router.get("/api/debug")
async def debug_probe() -> None:
    raise HTTPException(status_code=404, detail="Not found")

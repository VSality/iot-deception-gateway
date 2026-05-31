from fastapi import Request
from fastapi.responses import Response

from decision_logic.gateway import is_attacker
from shadow_world.decoys import match_decoy
from shadow_world.jitter import apply_shadow_jitter


async def shadow_decoy_middleware(request: Request, call_next):
    if await is_attacker(request):
        decoy = match_decoy(request.url.path)
        if decoy is not None:
            await apply_shadow_jitter()
            return Response(
                content=decoy.body,
                status_code=decoy.status_code,
                media_type=decoy.media_type,
            )
    return await call_next(request)

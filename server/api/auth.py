from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from decision_logic.gateway import is_attacker, record_real_session
from detection_module.analyzer import process_failed_ha_login

router = APIRouter(tags=["home-assistant-auth"])

HA_LOGIN_USER = "admin"
HA_LOGIN_PASSWORD = "admin"


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/api/auth/login")
async def ha_login(request: Request, body: LoginBody) -> dict:
    if await is_attacker(request):
        print("[SHADOW] Fake HA login success for isolated client (trap)")
        return {"result": "ok"}

    if body.username == HA_LOGIN_USER and body.password == HA_LOGIN_PASSWORD:
        record_real_session(request)
        print("[REAL] HA login success")
        return {"result": "ok"}

    await process_failed_ha_login(request)
    raise HTTPException(status_code=401, detail="Invalid credentials")

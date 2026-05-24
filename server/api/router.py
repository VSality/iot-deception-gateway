from fastapi import APIRouter

from api.lights import router as lights_router
from api.locks import router as locks_router
from api.states import router as states_router

api_router = APIRouter()
api_router.include_router(lights_router)
api_router.include_router(locks_router)
api_router.include_router(states_router)

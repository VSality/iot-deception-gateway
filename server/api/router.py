from fastapi import APIRouter, Depends

from api.auth import router as auth_router
from api.dev import router as dev_router
from api.lights import router as lights_router
from api.locks import router as locks_router
from api.states import router as states_router
from api.topology import router as topology_router
from detection_module.analyzer import monitor_traffic

api_router = APIRouter(dependencies=[Depends(monitor_traffic)])
api_router.include_router(auth_router)
api_router.include_router(lights_router)
api_router.include_router(locks_router)
api_router.include_router(states_router)
api_router.include_router(topology_router)
api_router.include_router(dev_router)

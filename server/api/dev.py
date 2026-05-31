import os

from fastapi import APIRouter, HTTPException, Request

from detection_module.analyzer import DETECTOR_IDS, emit_detection_hit

router = APIRouter(tags=["dev"])


def _sim_enabled() -> bool:
    return os.getenv("ENABLE_DETECTOR_SIM", "").lower() in ("1", "true", "yes")


@router.post("/api/dev/simulate-detection/{detector_id}")
async def simulate_detection(detector_id: str, request: Request) -> dict:
    if not _sim_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    if detector_id not in DETECTOR_IDS:
        raise HTTPException(status_code=404, detail="Not found")

    from decision_logic.client_identity import client_display_label, client_key

    message = f"[sim] Detector {detector_id} triggered"
    await emit_detection_hit(detector_id, message, request)
    return {
        "ok": True,
        "detector": detector_id,
        "client": client_display_label(client_key(request)),
    }

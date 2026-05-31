import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.router import api_router
from detection_module.analyzer import monitor_traffic
from error_masking import mask_server_header_middleware, register_error_masking
from shadow_world.decoy_middleware import shadow_decoy_middleware
from ws.dashboard import register_dashboard_websocket

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
INDEX_HTML = FRONTEND_DIR / "templates" / "index.html"

if not STATIC_DIR.is_dir():
    raise RuntimeError(f"Frontend static directory not found: {STATIC_DIR}")
if not INDEX_HTML.is_file():
    raise RuntimeError(f"Dashboard index not found: {INDEX_HTML}")

_enable_docs = os.getenv("ENABLE_DOCS", "").lower() in ("1", "true", "yes")

app = FastAPI(
    title="IoT Deception Gateway",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

register_error_masking(app)
app.middleware("http")(mask_server_header_middleware)
app.middleware("http")(shadow_decoy_middleware)

register_dashboard_websocket(app)

app.include_router(api_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def dashboard(_: None = Depends(monitor_traffic)) -> FileResponse:
    return FileResponse(INDEX_HTML, media_type="text/html")


@app.get("/{full_path:path}")
async def unknown_path(full_path: str, _: None = Depends(monitor_traffic)) -> None:
    # Lets global monitor_traffic run on honeypot probe URLs (no dedicated handler).
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

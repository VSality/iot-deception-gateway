import os

from fastapi import Depends, FastAPI, HTTPException

from api.router import api_router
from detection_module.analyzer import monitor_traffic
from error_masking import mask_server_header_middleware, register_error_masking

_enable_docs = os.getenv("ENABLE_DOCS", "").lower() in ("1", "true", "yes")

app = FastAPI(
    title="IoT Deception Gateway",
    dependencies=[Depends(monitor_traffic)],
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

register_error_masking(app)
app.middleware("http")(mask_server_header_middleware)

app.include_router(api_router)


@app.get("/{full_path:path}")
async def unknown_path(full_path: str) -> None:
    # Lets global monitor_traffic run on honeypot probe URLs (no dedicated handler).
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

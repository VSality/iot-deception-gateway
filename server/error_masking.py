from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

NGINX_SERVER_BANNER = "nginx/1.18.0"

_NGINX_TITLES = {
    400: "400 Bad Request",
    403: "403 Forbidden",
    404: "404 Not Found",
    405: "405 Not Allowed",
    422: "400 Bad Request",
    500: "500 Internal Server Error",
}


def _is_api_path(path: str) -> bool:
    return path.startswith("/api/")


def _iot_error_message(status_code: int) -> str:
    if status_code >= 500:
        return "Service temporarily unavailable"
    if status_code == 422:
        return "Invalid request parameters"
    return "Resource unavailable or missing"


def _iot_error_body(status_code: int) -> dict:
    return {
        "error_code": status_code,
        "message": _iot_error_message(status_code),
    }


def _nginx_html(status_code: int) -> str:
    title = _NGINX_TITLES.get(status_code, f"{status_code} Error")
    return f"""<html>
<head><title>{title}</title></head>
<body>
<center><h1>{title}</h1></center>
<hr><center>{NGINX_SERVER_BANNER}</center>
</body>
</html>"""


def _log_masked_error(path: str, status_code: int, internal_detail: object) -> None:
    print(
        f"[MASKED_ERROR] path={path} status={status_code} internal={internal_detail!r}"
    )


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> Response:
    path = request.url.path
    _log_masked_error(path, exc.status_code, exc.detail)

    if _is_api_path(path):
        return JSONResponse(
            status_code=exc.status_code,
            content=_iot_error_body(exc.status_code),
        )

    return HTMLResponse(
        content=_nginx_html(exc.status_code),
        status_code=exc.status_code,
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> Response:
    path = request.url.path
    status_code = 422
    _log_masked_error(path, status_code, exc.errors())

    if _is_api_path(path):
        return JSONResponse(
            status_code=status_code,
            content=_iot_error_body(status_code),
        )

    return HTMLResponse(
        content=_nginx_html(400),
        status_code=400,
    )


def register_error_masking(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)


async def mask_server_header_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["server"] = NGINX_SERVER_BANNER
    return response

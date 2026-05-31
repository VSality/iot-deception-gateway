import asyncio


async def broadcast_dashboard_log(level: str, message: str) -> None:
    from utils.ws_events import log_event
    from ws.dashboard import manager

    await manager.broadcast_json(log_event(level, message))


def schedule_dashboard_log(level: str, message: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_dashboard_log(level, message))


async def broadcast_device_state(
    device_id: str, state: str, device_type: str | None = None
) -> None:
    from utils.ws_events import device_state_event
    from ws.dashboard import manager

    await manager.broadcast_json(device_state_event(device_id, state, device_type))


def schedule_device_state(
    device_id: str, state: str, device_type: str | None = None
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_device_state(device_id, state, device_type))


async def broadcast_attack_alert(
    detector: str, message: str, client_ip: str = ""
) -> None:
    from utils.ws_events import attack_alert_event
    from ws.dashboard import manager

    await manager.broadcast_json(attack_alert_event(detector, message, client_ip))


def schedule_attack_alert(detector: str, message: str, client_ip: str = "") -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_attack_alert(detector, message, client_ip))


async def broadcast_reauth_success(client_label: str) -> None:
    from utils.ws_events import reauth_success_event
    from ws.dashboard import manager

    await manager.broadcast_json(reauth_success_event(client_label))


async def _reauth_then_ip_state(client_label: str) -> None:
    from decision_logic.gateway import _broadcast_ip_state

    await broadcast_reauth_success(client_label)
    await _broadcast_ip_state()


def schedule_reauth_success(client_label: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_reauth_then_ip_state(client_label))


async def broadcast_knock_progress(step: int) -> None:
    from utils.ws_events import knock_progress_event
    from ws.dashboard import manager

    await manager.broadcast_json(knock_progress_event(step))


def schedule_knock_progress(step: int) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_knock_progress(step))


async def broadcast_knock_reset() -> None:
    from utils.ws_events import knock_reset_event
    from ws.dashboard import manager

    await manager.broadcast_json(knock_reset_event())


def schedule_knock_reset() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_knock_reset())

"""Track the FastAPI/uvicorn event loop for cross-thread async scheduling."""

import asyncio

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Register the application event loop (called once at startup)."""
    global _main_loop
    _main_loop = loop


def get_main_event_loop() -> asyncio.AbstractEventLoop | None:
    """Return the registered application event loop, if any."""
    return _main_loop


async def run_on_main_loop(awaitable):
    """
    Await a coroutine on the main application loop.

    When called from a background workflow thread, schedules work on the main
    loop so WebSocket broadcasts remain safe.
    """
    main = get_main_event_loop()
    try:
        current = asyncio.get_running_loop()
    except RuntimeError:
        current = None
    if main is None or current is main:
        return await awaitable
    future = asyncio.run_coroutine_threadsafe(awaitable, main)
    return await asyncio.wrap_future(future)

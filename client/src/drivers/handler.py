import httpx
import logging
import os
import signal
import sys
import threading
import uvicorn
import webbrowser

from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from time import perf_counter, time

from src.adapters.services.encryption_adapter import EncryptionAdapter
from src.adapters.services.file_loader_adapter import FileLoaderAdapter
from src.adapters.services.handshake_adapter import HandshakeAdapter
from src.infrastructure.config.settings import get_settings
from src.infrastructure.logging.logging_configure import configure_logging
from src.infrastructure.logging.logging_profiler import profiler
from src.routers.map import MapRouter
from src.utils.get_elapsed import get_elapsed

configure_logging(save=False, json=False)
logger = logging.getLogger(__name__)


# Shuts uvicorn up.
SILENT_UVICORN = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(message)s"},
    },
    "handlers": {
        "default": {
            "class": "logging.FileHandler",
            "filename": "logs/uvicorn.log",
            "mode": "a",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"level": "INFO"},
    },
}


@asynccontextmanager
async def lifespan(app: Starlette):
    """Function controlling the whole lifecycle of the system."""

    logger.info("Configuring system...")
    start_time = perf_counter()
    profiling = {}

    settings = get_settings()

    # Preload all systems into memory to save startup time.
    # Profiler records all startup times to be logged.
    with profiler("encryption") as encryption_profiling:
        encryption_adapter = EncryptionAdapter(seed=settings.encryption_seed)

    profiling.update(encryption_profiling)

    # Preload the files as well.
    with profiler("file_loader") as file_loader_profiling:
        file_loader_adapter = FileLoaderAdapter()
        await file_loader_adapter.preload_files()

    profiling.update(file_loader_profiling)

    # Handshake system needs to get its key.
    with profiler("handshake") as handshake_profiling:
        key_pass = None

        if settings.private_key_password:
            key_pass = settings.private_key_password.encode("utf-8")

        handshake_adapter = HandshakeAdapter(
            private_key_path=settings.private_key_path, key_password=key_pass
        )

    profiling.update(handshake_profiling)

    # Responsible for server exchanges.
    with profiler("httpx") as httpx_profiling:
        httpx_client = httpx.AsyncClient()

    profiling.update(httpx_profiling)

    # Router where the map is actually defined.
    with profiler("map_router") as map_router_profiling:
        map_router = MapRouter(
            settings=settings,
            encryption=encryption_adapter,
            file_loader=file_loader_adapter,
            httpx_client=httpx_client,
        )
        app.state.map_router = map_router

    profiling.update(map_router_profiling)

    if not settings.test_mode:
        logger.info("Executing initial Server Handshake...")
        try:
            handshake_payload = {
                "username": settings.username,
                "timestamp": int(time()),
                "action": "authenticate",
            }
            signature = handshake_adapter.sign_payload(handshake_payload)

            response = await httpx_client.post(
                f"{settings.server}/api/handshake",
                json={
                    "payload": handshake_payload,
                    "signature": signature,
                },
                timeout=5.0,
            )

            if response.status_code == 200:
                logger.info("Handshake successful")

            else:
                logger.error(
                    "Handshake with server failed",
                    extra={"code": response.status_code},
                    exc_info=True,
                )

        except httpx.RequestError:
            logger.error(
                "Handshake request failed",
                exc_info=True,
            )

        except Exception:
            logger.error(
                "Unknown error during handshake",
                exc_info=True,
            )

    else:
        logger.warning("Test mode active, handshake skipped")

    profiling["duration"] = get_elapsed(start_time)
    logger.info(
        "System configuration finished",
        extra={"profiling": profiling},
    )

    yield

    logger.info("Shutting down system")
    await httpx_client.aclose()
    logger.info("System shut down")


# Endpoint routes.
async def shutdown_server(request: Request) -> JSONResponse:
    """Kills the server to prevent it from running silently in the background."""

    logger.info("Shutdown requested")
    os.kill(os.getpid(), signal.SIGTERM)
    return JSONResponse({"status": "Shutting down map display. Close the window."})


async def health_check(request: Request) -> JSONResponse:
    """Simple endpoint for checking status."""

    return JSONResponse({"status": "ok"})


async def get_background(request: Request):
    """Endpoint for getting the background map image from the localhost API."""

    return await request.app.state.map_router.get_background(request)


async def synchronize_data(request: Request):
    """Endpoint for data synchronization, shares the data with the map."""

    return await request.app.state.map_router.synchronize_data(request)


async def get_map_info(request: Request):
    """Endpoint for getting map data, it ensures the map size is accurate."""

    return await request.app.state.map_router.get_map_info(request)


async def display_map(request: Request):
    """Endpoint for actually displaying the map, the most important one for the user."""

    return await request.app.state.map_router.display_map(request)


# Starlette application.
app = Starlette(
    debug=False,
    routes=[
        Route("/shutdown", shutdown_server, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/api/background.img", get_background, methods=["GET"]),
        Route("/api/data", synchronize_data, methods=["GET"]),
        Route("/api/map", get_map_info, methods=["GET"]),
        Route("/", display_map, methods=["GET"]),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    if sys.executable.endswith("WT-Datalink.exe"):
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")

    settings_cached = get_settings()
    url = f"http://127.0.0.1:{settings_cached.local_map_port}"

    logger.info(
        "Starting client",
        extra={"address": url},
    )

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings_cached.local_map_port,
        log_config=SILENT_UVICORN,
    )

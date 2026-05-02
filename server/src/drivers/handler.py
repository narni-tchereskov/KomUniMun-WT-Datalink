import logging
import uvicorn

from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from time import perf_counter

from src.adapters.services.encryption_adapter import EncryptionAdapter
from src.adapters.services.handshake_validator_adapter import HandshakeValidatorAdapter
from src.infrastructure.config.settings import get_settings
from src.infrastructure.logging.logging_configure import configure_logging
from src.infrastructure.logging.logging_profiler import profiler
from src.routers.synchronizer import SynchronizerRouter
from src.utils.get_elapsed import get_elapsed

configure_logging(save=False, json=False)
logger = logging.getLogger(__name__)


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

    # Handshake system needs to get its keys.
    with profiler("handshake") as handshake_profiling:
        handshake_validator_adapter = HandshakeValidatorAdapter(
            keys_folder_path=settings.public_key_folder
        )

    profiling.update(handshake_profiling)

    # Router where the synchronizer is actually defined.
    with profiler("synchronizer_router") as synchronizer_router_profiling:
        synchronizer_router = SynchronizerRouter(
            settings=settings,
            encryption=encryption_adapter,
            handshake_validator=handshake_validator_adapter,
        )
        app.state.synchronizer_router = synchronizer_router

    profiling.update(synchronizer_router_profiling)

    profiling["duration"] = get_elapsed(start_time)
    logger.info(
        "System configuration finished",
        extra={"profiling": profiling},
    )

    yield

    logger.info("Shutting down system")


# Endpoint routes.
async def health_check(request: Request) -> JSONResponse:
    """Simple endpoint for checking status."""

    return JSONResponse({"status": "ok"})


async def authenticate_client(request: Request) -> JSONResponse:
    """Validates a handshake to authenticate an user to the system."""

    return await request.app.state.synchronizer_router.authenticate_client(request)


async def synchronize_data(request: Request) -> JSONResponse:
    """Synchronizes data from the request sent by an user."""

    return await request.app.state.synchronizer_router.synchronize_data(request)


# Starlette application.
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/api/handshake", authenticate_client, methods=["POST"]),
        Route("/api/synchronizer", synchronize_data, methods=["POST"]),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    settings_cached = get_settings()

    logger.info(
        "Starting server",
        extra={"port": settings_cached.port},
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings_cached.port,
        log_level="info",
    )

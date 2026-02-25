"""Oiduna HTTP API Server

Real-time SuperDirt/MIDI loop engine with HTTP REST API.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oiduna_api.config import settings
from oiduna_api.extensions import discover_extensions
from oiduna_api.routes import assets, dashboard, midi, patterns, playback, scene, stream, tracks
from oiduna_api.services.loop_service import LoopService, get_loop_service, lifespan

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_wrapper(app: FastAPI):
    """
    FastAPI lifespan manager with extension system integration.

    Lifecycle:
    1. Auto-discover extensions via entry_points
    2. Run extension startup hooks
    3. Collect runtime hooks for loop_engine
    4. Start loop_engine with hooks
    5. Register extension routers
    6. [App runs]
    7. Stop loop_engine
    8. Run extension shutdown hooks
    """
    # 1. Auto-discover and register extensions
    pipeline = discover_extensions()
    app.state.extension_pipeline = pipeline

    # 2. Run extension startup hooks
    await pipeline.startup_all()

    # 3. Collect runtime hooks
    before_send_hooks = pipeline.get_send_hooks()

    # 4. Start loop_engine with extension hooks
    async with lifespan(
        osc_host=settings.osc_host,
        osc_port=settings.osc_port,
        receive_port=settings.osc_receive_port,
        midi_port_name=settings.midi_port,
        before_send_hooks=before_send_hooks,
    ):
        # 5. Register extension routers (must be before app starts accepting requests)
        for name, ext in pipeline.extensions:
            router = ext.get_router()
            if router is not None:
                app.include_router(router)
                logger.info(f"Registered router from extension: {name}")

        yield

        # 6. Run extension shutdown hooks
        await pipeline.shutdown_all()


# Create FastAPI app
app = FastAPI(
    title="Oiduna API",
    version="0.1.0",
    description="Real-time SuperDirt/MIDI loop engine HTTP API",
    lifespan=lifespan_wrapper,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(patterns.router, prefix="/patterns", tags=["patterns"])
app.include_router(playback.router, prefix="/playback", tags=["playback"])
app.include_router(stream.router, tags=["stream"])
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(scene.router, prefix="/scene", tags=["scene"])
app.include_router(midi.router, prefix="/midi", tags=["midi"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])


# @app.get("/")
# async def root():
#     """Root endpoint with API information"""
#     return {
#         "name": "Oiduna API",
#         "version": "0.1.0",
#         "description": "Real-time SuperDirt/MIDI loop engine HTTP API",
#         "docs": "/docs",
#         "health": "/health",
#     }


@app.get("/health")
async def health(loop_service: LoopService = Depends(get_loop_service)):
    """Enhanced health check with connection status"""
    engine = loop_service.get_engine()

    # OSC connection (SuperDirt)
    osc = engine._osc
    osc_info = {
        "connected": osc.is_connected,
        "host": osc._host,
        "port": osc._port,
    }

    # MIDI connection (may fail if no MIDI devices available)
    midi = engine._midi
    try:
        available_ports = midi.list_ports()
        midi_info = {
            "connected": midi.is_connected,
            "port": midi.port_name,
            "available_ports": available_ports,
        }
    except Exception as e:
        midi_info = {
            "connected": False,
            "port": None,
            "available_ports": [],
            "error": str(e),
        }

    # Engine status
    engine_info = {
        "running": engine._running,
        "bpm": engine.state.bpm,
    }

    # Overall status
    overall_status = "healthy" if osc_info["connected"] else "degraded"

    return {
        "status": overall_status,
        "version": app.version,
        "components": {
            "osc": osc_info,
            "midi": midi_info,
            "engine": engine_info,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oiduna_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

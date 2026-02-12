"""Oiduna HTTP API Server

Real-time SuperDirt/MIDI loop engine with HTTP REST API.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oiduna_api.config import settings
from oiduna_api.routes import assets, dashboard, midi, playback, scene, stream, tracks, trigger
from oiduna_api.services.loop_service import LoopService, get_loop_service, lifespan


@asynccontextmanager
async def lifespan_wrapper(app: FastAPI):
    """FastAPI lifespan manager"""
    async with lifespan(
        osc_host=settings.osc_host,
        osc_port=settings.osc_port,
        midi_port_name=settings.midi_port,
    ):
        yield


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
app.include_router(playback.router, prefix="/playback", tags=["playback"])
app.include_router(trigger.router, prefix="/trigger", tags=["trigger"])
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

    # SuperDirt connection
    backend = engine._backend
    sender = backend.get_sender()
    superdirt_info = {
        "connected": sender.is_connected,
        "host": backend._host,
        "port": backend._port,
    }

    # MIDI connection
    midi = engine._midi
    midi_info = {
        "connected": midi.is_connected,
        "port": midi.port_name,
        "available_ports": midi.list_ports(),
    }

    # Engine status
    engine_info = {
        "running": engine._running,
        "bpm": engine.state.environment.bpm,
    }

    # Overall status
    overall_status = "ok" if superdirt_info["connected"] else "degraded"

    return {
        "status": overall_status,
        "superdirt": superdirt_info,
        "midi": midi_info,
        "engine": engine_info,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oiduna_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

"""Oiduna HTTP API Server

Real-time SuperDirt/MIDI loop engine with HTTP REST API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oiduna_api.config import settings
from oiduna_api.routes import assets, midi, playback, scene, stream, tracks
from oiduna_api.services.loop_service import lifespan


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

# Include routers
app.include_router(playback.router, prefix="/playback", tags=["playback"])
app.include_router(stream.router, tags=["stream"])
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(scene.router, prefix="/scene", tags=["scene"])
app.include_router(midi.router, prefix="/midi", tags=["midi"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Oiduna API",
        "version": "0.1.0",
        "description": "Real-time SuperDirt/MIDI loop engine HTTP API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oiduna_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

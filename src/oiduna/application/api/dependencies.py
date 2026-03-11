"""FastAPI dependencies for Oiduna API."""

from fastapi import Request

from oiduna.application.api.extensions import ExtensionPipeline
from oiduna.application.api.services.loop_service import get_loop_service
from oiduna.domain.session import SessionContainer


# Singleton SessionContainer instance
_container: SessionContainer | None = None


def get_container() -> SessionContainer:
    """
    Get the singleton SessionContainer instance.

    On first call, injects the event publisher from LoopService for SSE events.

    Usage:
        @router.get("/tracks")
        async def list_tracks(
            container: SessionContainer = Depends(get_container)
        ):
            return container.tracks.list_tracks()
    """
    global _container
    if _container is None:
        # Get event publisher from LoopService
        event_publisher = None
        try:
            loop_service = get_loop_service()
            event_publisher = loop_service.get_state_producer()
        except RuntimeError:
            # LoopService not initialized yet (e.g., during testing)
            pass

        _container = SessionContainer(event_publisher=event_publisher)
    return _container


def get_pipeline(request: Request) -> ExtensionPipeline:
    """
    Dependency to get the extension pipeline.

    Usage:
        @router.post("/session")
        async def load_session(
            pipeline: ExtensionPipeline = Depends(get_pipeline)
        ):
            payload = pipeline.apply(req.model_dump())
            ...
    """
    return request.app.state.extension_pipeline

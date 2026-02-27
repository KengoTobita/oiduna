"""FastAPI dependencies for Oiduna API."""

from fastapi import Request

from oiduna_api.extensions import ExtensionPipeline
from oiduna_api.services.loop_service import get_loop_service
from oiduna_session import SessionManager


# Singleton SessionManager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Get the singleton SessionManager instance.

    On first call, injects the event sink from LoopService for SSE events.

    Usage:
        @router.get("/tracks")
        async def list_tracks(
            manager: SessionManager = Depends(get_session_manager)
        ):
            return manager.list_tracks()
    """
    global _session_manager
    if _session_manager is None:
        # Get event sink from LoopService
        event_sink = None
        try:
            loop_service = get_loop_service()
            event_sink = loop_service.get_state_sink()
        except RuntimeError:
            # LoopService not initialized yet (e.g., during testing)
            pass

        _session_manager = SessionManager(event_sink=event_sink)
    return _session_manager


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
